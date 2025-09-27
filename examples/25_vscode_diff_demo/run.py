import argparse
from pathlib import Path

import uvicorn

from openhands.agent_server.api import create_app
from openhands.agent_server.config import Config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    # Load config from this example directory
    config_path = Path(__file__).with_name("config.json")
    config = Config.from_json_file(config_path)

    # Resolve static_files_path relative to this example directory, if set
    if config.static_files_path is not None:
        static_dir = (
            config.static_files_path
            if config.static_files_path.is_absolute()
            else config_path.parent / config.static_files_path
        )
        config = config.model_copy(update={"static_files_path": static_dir})

    # Create the agent server app with our config; it serves /static and /api
    app = create_app(config)

    # Run the demo app
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
