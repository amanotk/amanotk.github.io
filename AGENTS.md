# Repo Notes

## Git / SSH in WSL

- This repo has `.python-version` set to `3.12`.
- In this environment, `ssh` may resolve to `~/.pyenv/shims/ssh` instead of `/usr/bin/ssh`.
- If that Python version is not installed, Git-over-SSH commands can fail before authentication with:
  - `pyenv: version '3.12' is not installed`

### Workaround

Use the system SSH binary explicitly for remote Git commands:

```bash
GIT_SSH_COMMAND="/usr/bin/ssh" git push
```

The same workaround applies to `git pull`, `git fetch`, and SSH auth checks:

```bash
GIT_SSH_COMMAND="/usr/bin/ssh" git fetch
GIT_SSH_COMMAND="/usr/bin/ssh" git pull
/usr/bin/ssh -T git@github.com
```

### Quick check

If GitHub SSH suddenly stops working, verify which binary is being used:

```bash
which ssh
```

If it points to a pyenv shim, prefer `/usr/bin/ssh` for Git remote operations in this repo.
