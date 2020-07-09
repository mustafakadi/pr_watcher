"""
Functionality definition of management class for the PR list
* This is a SINGLETON class
"""
import enum


class PRInProgressAction(enum.Enum):
    PR_REMOVED = 1
    PR_CANNOT_BE_REMOVED = 2
    PR_IN_PROGRESS_UPDATED = 3


class _PrNode:
    """
    Node definition for linked list structure
    """
    basic_pr = None
    next_pr_node = None


class PrListManager:

    """ Singleton reference of the class. """
    _instance = None

    """ Virtually private declaration of class constructor. """
    def __init__(self):
        if not PrListManager._instance:
            self.pr_root_node = None
            self.pr_id_to_remove = ""
            self.pr_id_in_progress = ""
            PrListManager._instance = self

    """ Method to retrieve the reference to the singleton class object. """
    @staticmethod
    def get_instance():
        if not PrListManager._instance:
            PrListManager()
        return PrListManager._instance

    """
    Adds the new pr to the linked list, if it is not already added.
    :param watch_pr_item: *BasicPR* object to be added to the linked list
    :returns: True, if the pr is added successfully, False, otherwise
    """
    def add_pr(self, watch_pr_item):
        if not watch_pr_item:
            return False

        if not self.pr_root_node:
            tmp_pr_node = _PrNode()
            tmp_pr_node.basic_pr = watch_pr_item
            tmp_pr_node.next_pr_node = None
            self.pr_root_node = tmp_pr_node
            return True

        tmp_pr_node = self.pr_root_node
        if tmp_pr_node.basic_pr.id == watch_pr_item.id:
            return False
        while tmp_pr_node.next_pr_node:
            tmp_pr_node = tmp_pr_node.next_pr_node
            if tmp_pr_node.basic_pr.id == watch_pr_item.id:
                return False
        curr_pr_node = _PrNode()
        curr_pr_node.basic_pr = watch_pr_item
        curr_pr_node.next_pr_node = None
        tmp_pr_node.next_pr_node = curr_pr_node
        return True

    """
    Removes the PR item with the corresponding id form to the linked list, if it already exists.
    :param pr_id: String representation of the PR id to be removed from the linked list
    :returns: True, if the pr is removed successfully, False, otherwise
    """
    def remove_pr_from_list(self, pr_id):
        # Checks whether the corresponding PR item is already in execution by the check thread.
        # If it is indeed, store the id to be removed later, when check thread finishes using the PR item
        if self.pr_id_in_progress != pr_id:
            if not self.pr_root_node:
                return False

            if self.pr_root_node.basic_pr.id == pr_id:
                self.pr_root_node.basic_pr = None
                tmp_pr_node = self.pr_root_node.next_pr_node
                self.pr_root_node.next_pr_node = None
                self.pr_root_node = tmp_pr_node
                return True
            tmp_pr_node = self.pr_root_node
            while tmp_pr_node.next_pr_node is not None:
                tmp_next_node = tmp_pr_node.next_pr_node
                if tmp_next_node.basic_pr.id == pr_id:
                    tmp_pr_node.next_pr_node = tmp_next_node.next_pr_node
                    tmp_next_node.basic_pr = None
                    tmp_next_node.next_pr_node = None
                    return True
                tmp_pr_node = tmp_pr_node.next_pr_node
        else:
            self.pr_id_to_remove = pr_id
        return False

    """
    Updates the PR id in progress.
    :param pr_id: String representation of the PR id in progress by the check thread.
    """
    def update_pr_id_in_progress(self, pr_id):
        self.pr_id_in_progress = pr_id
        if self.pr_id_to_remove != pr_id:
            if self.remove_pr_from_list(self.pr_id_to_remove):
                self.pr_id_to_remove = ""
                return PRInProgressAction.PR_REMOVED
            return PRInProgressAction.PR_CANNOT_BE_REMOVED
        return PRInProgressAction.PR_IN_PROGRESS_UPDATED

    """
    Checks whether the PR item with given id exists or no
    :param pr_id: String representation of the PR id to be searched
    :returns: True, if PR exits, False, otherwise
    """
    def does_pr_item_exist(self, pr_id):
        tmp_pr_node = self.pr_root_node
        while tmp_pr_node:
            if tmp_pr_node.basic_pr and tmp_pr_node.basic_pr.id == pr_id:
                return True
            tmp_pr_node = tmp_pr_node.next_pr_node
        return False
