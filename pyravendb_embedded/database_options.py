class DatabaseOptions:
    def __init__(self, database_name=None, skip_creating_database=False):
        """
        The options when creating a new database

        :param database_name: The name of the database
        :param skip_creating_database: If True we will skip creating a new database when creating the store

        :type database_name: str
        :type skip_creating_database: bool
        """
        self.database_name = database_name
        self.skip_creating_database = skip_creating_database
