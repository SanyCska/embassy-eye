# Deployment Quick Reference

Use this checklist after pulling the latest code on the server to rebuild and restart the automation container cleanly.

## 1. Stop Existing Containers
```bash
docker ps --filter "name=embassy-eye"
docker stop embassy-eye || true
docker rm embassy-eye || true
```
The `|| true` keeps the script going if the container is already stopped or absent.

## 2. Remove Old Images (optional but keeps disk usage low)
```bash
docker image ls "embassy-eye*"
docker image rm embassy-eye_embassy-eye || true
```
Skip this if you want Docker to reuse cached layers during build.

## 3. Update Source Code
```bash
cd /path/to/embassy-eye
git pull --rebase
```
Verify there are no local changes blocking the pull before continuing.

## 4. Rebuild and Start
```bash
./build_docker.sh        # only rebuilds if necessary
docker-compose up --build --remove-orphans -d embassy-eye
```
`build_docker.sh` caches hashes for fast rebuilds. `--remove-orphans` cleans up outdated service containers.

## 5. Verify Logs
```bash
docker logs -f embassy-eye
```
Confirm Selenium and booking steps run without errors. Press `Ctrl+C` to exit log tailing.

