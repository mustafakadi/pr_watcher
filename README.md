# PR Watcher

PR Watcher is a lightweight and easy-to-use system tray Python application that can be used for tracking the statuses of the pull requests from Bitbucket. PR Watcher uses the Bitbucket API for retrieving the information about the pull requests.

- It can support multiple pull requests and it shows the build statuses of the registered pull requests.
- When there is an update in the status or the comments of the pull request, it automatically informs the user about the update with a pop-up.
- Domain address, API version, project name and the repository name can be set to customize the tracking options.
- It stores the repository information in the registry, so it does not require the user to re-enter the customized options every time the application is opened.
- The supported pull request statuses are:
  - Failed
  - Success
  - In progress
  - Conflict
  - Merged
  - Ready to merge

PR Watcher does not require any username or password to be able to use the Bitbucket API. To have a more secure approach, it only requires an access token that can be easily created from Bitbucket user profile.

### Tech
PR Watcher uses [PyQt5] for GUI.

### Installation
It can be easily deployed with pyinstaller.

### Todos:
- Cleaning the code
- Adding capability to merge a PR through the application, when the PR is ready to merge
- Adding support for PR specific domain address, API version, project name and the repository name to track PRs from different places at the same
- Adding tests
