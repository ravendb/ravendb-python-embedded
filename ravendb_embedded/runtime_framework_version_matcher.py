from __future__ import annotations
import subprocess
from enum import Enum
from typing import Optional, Tuple, List

from ravendb_embedded.options import ServerOptions


class MatchingType(Enum):
    EQUAL = 1
    GREATER_OR_EQUAL = 2


class RuntimeFrameworkVersionMatcher:
    WILDCARD = "x"
    GREATER_OR_EQUAL = "+"

    @classmethod
    def match(cls, options: ServerOptions) -> str:
        if not cls.needs_match(options):
            return options.framework_version

        runtime = RuntimeFrameworkVersion(options.framework_version)
        runtimes = cls.get_framework_versions(options)

        return cls.match_runtime(runtime, runtimes)

    @staticmethod
    def match_runtime(runtime: RuntimeFrameworkVersion, runtimes: List[RuntimeFrameworkVersion]) -> str:
        sorted_runtimes = sorted(runtimes, key=lambda x: (x.major, x.minor, x.patch), reverse=True)

        for version in sorted_runtimes:
            if runtime.match(version):
                return str(version)

        available_runtimes = "- ".join([str(r) for r in sorted_runtimes])
        raise RuntimeError(
            f"Could not find a matching runtime for '{runtime}'. Available runtimes:\n- {available_runtimes}"
        )

    @classmethod
    def needs_match(cls, options: ServerOptions) -> bool:
        if not options or not options.framework_version:
            return False

        framework_version = options.framework_version.lower()
        if cls.WILDCARD not in framework_version and cls.GREATER_OR_EQUAL not in framework_version:
            return False

        return True

    @staticmethod
    def get_framework_versions(options: ServerOptions):
        if not options.dot_net_path:
            raise RuntimeError("Dotnet path is not provided.")

        process_command = [options.dot_net_path, "--info"]
        runtimes = []

        try:
            with subprocess.Popen(
                process_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ) as process:
                inside_runtimes = False
                runtime_lines = []

                for line in process.stdout:
                    line = line.strip()
                    if line.startswith(".NET runtimes installed:") or line.startswith(".NET Core runtimes installed:"):
                        inside_runtimes = True
                        continue
                    if inside_runtimes and line.startswith("Microsoft.NETCore.App"):
                        runtime_lines.append(line)

                for runtime_line in runtime_lines:
                    values = runtime_line.split(" ")
                    if len(values) < 2:
                        raise RuntimeError(
                            f"Invalid runtime line. Expected 'Microsoft.NETCore.App x.x.x', but was '{runtime_line}'"
                        )
                    runtimes.append(RuntimeFrameworkVersion(values[1]))

        except Exception as e:
            raise RuntimeError("Unable to execute dotnet to retrieve list of installed runtimes") from e
        finally:
            if process:
                process.kill()
        return runtimes


class RuntimeFrameworkVersion:
    SEPARATORS = "."
    SUFFIX_SEPARATOR = "-"

    def __init__(self, framework_version: str):
        self.major: Optional[int] = None
        self.minor: Optional[int] = None
        self.patch: Optional[int] = None
        self._patch_matching_type: Optional[MatchingType] = None

        framework_version = framework_version.lower()

        suffixes = [s for s in framework_version.split(self.SUFFIX_SEPARATOR) if s.strip()]
        if len(suffixes) != 1:
            framework_version = suffixes[0]
            self.suffix = self.SUFFIX_SEPARATOR.join(suffixes[1:])
        else:
            self.suffix = None

        versions = [v.strip() for v in framework_version.split(self.SEPARATORS) if v.strip()]
        for i, version in enumerate(versions):
            if RuntimeFrameworkVersionMatcher.WILDCARD not in version:
                tuple_values = self.parse(version)
                self._set(i, version, *tuple_values)
                continue

            if version != RuntimeFrameworkVersionMatcher.WILDCARD:
                raise RuntimeError(f"Wildcard character must be a sole part of the version string, but was '{version}'")

            self._set(i, None, None, MatchingType.EQUAL)

    @property
    def patch_matching_type(self) -> MatchingType:
        return self._patch_matching_type

    @staticmethod
    def to_string_interval(number: Optional[int], matching_type: MatchingType):
        if number is None:
            return RuntimeFrameworkVersionMatcher.WILDCARD

        if matching_type == MatchingType.EQUAL:
            return str(number)
        elif matching_type == MatchingType.GREATER_OR_EQUAL:
            return f"{number}{RuntimeFrameworkVersionMatcher.GREATER_OR_EQUAL}"
        else:
            raise ValueError(f"Invalid matching type: {matching_type}")

    def __str__(self):
        s1 = self.to_string_interval(self.major, MatchingType.EQUAL)
        s2 = self.to_string_interval(self.minor, MatchingType.EQUAL)
        s3 = self.to_string_interval(self.patch, self.patch_matching_type)

        version = f"{s1}.{s2}.{s3}"

        if self.suffix:
            version += f"{self.SUFFIX_SEPARATOR}{self.suffix}"

        return version

    @staticmethod
    def parse(value: str) -> Tuple[int, MatchingType]:
        matching_type = MatchingType.EQUAL

        value_to_parse = value

        last_char = value_to_parse[-1]
        if last_char == RuntimeFrameworkVersionMatcher.GREATER_OR_EQUAL:
            matching_type = MatchingType.GREATER_OR_EQUAL
            value_to_parse = value_to_parse[:-1]

        value_as_int = int(value_to_parse)
        return value_as_int, matching_type

    def _set(
        self,
        i: int,
        value_as_string: Optional[str],
        value: Optional[int],
        matching_type: MatchingType,
    ) -> None:
        if i == 0:
            self.assert_matching_type("major", value_as_string, MatchingType.EQUAL, matching_type)
            self.major = value
        elif i == 1:
            self.assert_matching_type("minor", value_as_string, MatchingType.EQUAL, matching_type)
            self.minor = value
        elif i == 2:
            self.assert_matching_type("patch", value_as_string, None, matching_type)
            self.patch = value
            self._patch_matching_type = matching_type
        else:
            raise ValueError()

    def assert_matching_type(
        self,
        field_name: str,
        value_as_string: str,
        expected_matching_type: Optional[MatchingType],
        matching_type: MatchingType,
    ) -> None:
        if self.suffix and matching_type != MatchingType.EQUAL:
            raise RuntimeError(
                f"Cannot set '{field_name}' with value '{value_as_string}' "
                f"because '{self.matching_type_to_string(matching_type)}' "
                f"is not allowed when suffix ('{self.suffix}') is set."
            )

        if expected_matching_type is not None and expected_matching_type != matching_type:
            raise RuntimeError(
                f"Cannot set '{field_name}' with value '{value_as_string}' "
                f"because '{self.matching_type_to_string(matching_type)}' "
                "is not allowed."
            )

    @staticmethod
    def matching_type_to_string(matching_type):
        if matching_type == MatchingType.EQUAL:
            return ""
        elif matching_type == MatchingType.GREATER_OR_EQUAL:
            return str(RuntimeFrameworkVersionMatcher.GREATER_OR_EQUAL)
        else:
            raise ValueError(f"Illegal matching type: {matching_type}")

    def match(self, version: RuntimeFrameworkVersion) -> bool:
        if self.major is not None and self.major != version.major:
            return False

        if self.minor is not None and self.minor != version.minor:
            return False

        if self.patch is not None:
            if self.patch_matching_type == MatchingType.EQUAL and self.patch != version.patch:
                return False
            elif self.patch_matching_type == MatchingType.GREATER_OR_EQUAL and self.patch > version.patch:
                return False

        return self.suffix == version.suffix
