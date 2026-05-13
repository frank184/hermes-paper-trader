# Jupyter

Jupyter is an optional research surface for notebooks and model inspection.

## Service

```text
services/jupyter
```

Start with:

```bash
docker compose --profile notebooks up jupyter
```

Open:

```text
http://127.0.0.1:8888
```

## Mounts

```text
./notebooks -> /home/jovyan/work
./models    -> /home/jovyan/work/models
```

## Installed Extras

The image installs:

- `alpaca-py`
- `psycopg[binary]`

## Security

The port is bound to `127.0.0.1`. Token and XSRF checks are disabled to make VS Code remote-kernel usage reliable.

Do not publish this service on a public interface without restoring authentication.

## Restart Behavior

Notebook files are persisted through the `./notebooks` bind mount. Kernel processes are not persisted.

After `docker compose down` or a Jupyter container restart, VS Code may keep sending requests to an old kernel id and logs may show `Kernel does not exist`. Clear the saved Jupyter server in VS Code, reload the window, and reconnect to:

```text
http://127.0.0.1:8888
```

See [Notebooks](../NOTEBOOKS.md) for the step-by-step recovery flow.
