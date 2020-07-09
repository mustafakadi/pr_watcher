class RepoInfo:

    """ Singleton reference of the class """
    _instance = None

    """ Virtually private declaration of class constructor """
    def __init__(self):
        if not RepoInfo._instance:
            self.access_token = ""
            self.api_version = ""
            self.server_address = ""
            self.project_name = ""
            self.repo_name = ""
            RepoInfo._instance = self

    """ Method to retrieve the reference to the singleton class object """
    @staticmethod
    def get_instance():
        if not RepoInfo._instance:
            RepoInfo()
        return RepoInfo._instance

    @staticmethod
    def are_all_fields_set():
        if not RepoInfo._instance or not RepoInfo._instance.access_token or not RepoInfo._instance.api_version \
                or not RepoInfo._instance.server_address or not RepoInfo._instance.project_name \
                or not RepoInfo._instance.repo_name:
            return False
        return True
