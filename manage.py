from flask_script import (Manager, Shell, Server, prompt, prompt_pass, prompt_bool)
from impl import app

manager = Manager(app)

manager.add_command("runserver", Server("0.0.0.0", port=8080))

if __name__ == "__main__":
    manager.run()
