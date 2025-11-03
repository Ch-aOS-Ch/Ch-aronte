# Writting pyinfra successors for Ch-aronte

## TLDR:
`State`: Pyinfra session where all of your op's go.

`op`: Declarative operations from pyinfra.

`add_op()`: `op` pile made to be ran with `run_ops()`

why?: Cause pyinfra is significantly faster than ansible, and it allows for the use of python's ecosystem.

USE THE PYINFRA API, _NOT_ THE BINARY.

----


## Why?
Well, I _do_ have all of the systems working, why change this?
Simple: Cause ansible is slow. Pyinfra is fast as hell, and it allows for the use of python's ecosystem picture an "Ch-obolo" schema meant to verify if the Ch-obolo is valid before runing the systems, _this_ is why I'm making this switch.
Also, nix is not just a config file with a lot of semantics, it's a _programing_ language, with this system, I can show people _how_ to use something like OmegaConf to generate valid Ch-obolos, then validate it manually, then validate it automatically, just like nix, but with a middle portion meant to show people the "what" their system is going to become.

---

## First of all:
The docs. The documentation for Pyinfra is horrible at best, therefore I'm going to do the best of my efforts to explain what everything does and how the things should be setup, ok? ok.

First of all: whay is this?
```py
from pyinfra.api import State, Config, Inventory
from pyinfra.api.connect import connect_all, disconnect_all
from pyinfra.api.state import StateStage
from pyinfra.context import ctx_state
```

These are pyinfra modules, they serve as normal modules, but they are very sparse and work weirdly because of--

## Secondly:
Pyinfra is not just an api, it is also a binary akin to python, this means they have a very convoluted system setup to serve both of these, worst of all, they use the same language AND have bad exceptions, so you can technically just import the wrong modules and python won't even notice.

## Thirdly: why?
```py
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
hosts = ["@local"]
inventory = Inventory((hosts, {{}}))
config = Config()
state = State(inventory, config)
state.current_stage = StateStage.Prepare # <~ btw, this is necessary
ctx_state.set(state)

print("Connecting to localhost...")
connect_all(state)
host = state.inventory.get_host("@local")
print("Connection established.")
```

Yeah, remember when I said it's not just an API, but a binary as well? Yeah, this is why this is an issue.
You see, since pyinfra is an ansible alternative, they need to have a way to connect to your pc and/or to other pcs, this is how they do it.
For this project, you'll probably see it just this once, but it is important to note it, since you'll need to use the state and host in the roles.

Oh yeah, forgot to mention. I use the API, _NOT_ the binary. Using the API opens up _all_ of python's systems and modules to be used, with the binary, I'd lose a lot of good (and native) imports.

## Fourthly: How to create the modules?

Well, It's a list
1. first you need to state the state of the state like so:
    ```py
    state.current_stage = StateStage.Prepare
    ```
    but of course I've already took care of that for you

2. About these weird... Things
   ```py
   if toAddNative:
    add_op(
        state,
        pacman.packages,
        name="Installing packages",
        packages=toAddNative,
        present=True,
        update=True,
        _sudo=True
    )
   if toRemoveNative:
    add_op(
        state,
        pacman.packages,
        name="Uninstalling packages",
        packages=toRemoveNative,
        present=False,
        update=True,
        _sudo=True
    )
   run_ops(state)
   ```

   Ok, let's be thorough about this.
   Pyinfra uses "Piles" to manage the state, you want to use `add_op()` to declare how and what the state should be. Thankfully, these adds are very intelligent, only passing what they need when they need it. For instance, I used pacman.packages, so the add knew what I meant by `update`, `packages`, `present` and `update`. `Name`s are universal, `state`s should always be declared and be the one passed by `main.py`.
   Oh, but we're not finished yet, cause you see that `_sudo` right there? Yeah, all things that start with _ are universal as well, you can just slap one of these badboys in any `op` (which means operation) and it'll work as the doc suggests.
   And finally, `run_ops()`, this is the _most_ important part of the system, you _need_ this to say "hey, pyinfra, I'm done adding things to the pile, make the state I passed to you match the state I declared", and it'll do it.
   Important notes: you can (and, IMO, should) _not_ use `_sudo_password` with `_sudo`, the first one declares what's going to be the password used by sudo, the second one only appends an big ol' "sudo" before any commands, when used together, sudo will know what to use, however, when using only `_sudo`, the system will automatically ask for the password, it's kinda neat, since it uses the native sudo security measures.

## Fifthly: OmegaConf
I use omegaconf as the thing that helps me parse the used Ch-obolo, it's very useful, you can simply do
```py
ChObolo = OmegaConf.load(ChOboloPath)
```
And every single one of your variables will be inside of `ChObolo`, so basically, you can simply do `ChObolo.users[0].shell` and get the shell of the first listed user, VERY handy whence I start remaking the scripts, since it can also just create the Ch-obolo itself, and also when I start making examples and comparing them to some `configurations.nix`'s.

## finally
So, these are my findings as of right now about this system, it IS a pain to use at first glance, but whence you understand how the thing actually works, it gets easier, also, it IS leagues faster than ansible, which is BIG.

How can you run this?
Firstly run `uv tool install omegaconf pyinfra`, then `uv add --dev omegaconf pyinfra`, then `uv run main.py [tags to use] -e path/to/ch-obolo/to-use.yml`
To do a dry run, simply switch the config on `main.py` to `config = Config(dry=True)`

# Creating your own Pyinfra Role
Here's a quick guide to get you started on creating a new role for Ch-aronte.

1.  **Create the File Structure:** Create your directory and Python file following the pattern: `roles/your_role/tasks/your_role.py`.

2.  **Define the Entry Point:** In your new file, create the main function that will be called by `main.py`. It must accept `state`, `host`, and `chobolo_path` as arguments.
    ```python
    def run_your_role(state, host, chobolo_path):
        # Your logic goes here
        print("Executing your_role!")
    ```

3.  **Implement Your Logic:** Use `add_op` and `run_ops` to execute your operations. Import any necessary `pyinfra.operations` at the top of your file.

4.  **Integrate with `main.py`:**
    *   Import your new role at the top of `main.py`:
        ```python
        from roles.your_role.tasks import your_role

        ```

    *   Add the corresponding `tag` to the `ROLES_DISPATCHER` block in `main.py`:
        ```python
        #...
        ROLES_DISPATCHER = {
          "packages": pkgs_role.run_all_pkg_logic,
          "your_role": your_role.run_your_role,
        }
        #...

        ```

    *   You can also create aliases for your tags in the `ROLE_ALIASES` block, it should map directly to the dispatcher variable.:
        ```py
        ROLE_ALIASES = {
            "pkgs": "packages",
            "yrrl": "your_role"
        }

## Minimal Example: A 'touch' Role
Here is a complete, minimal example of a role that creates a directory in `/tmp/`.

**File: `roles/touch/tasks/touch.py`**
```python
#!/usr/bin/env python3
from pyinfra.operations import server
from pyinfra.api.operation import add_op
from pyinfra.api.operations import run_ops

# Note: We don't need OmegaConf if the role doesn't read the Ch-obolo file.

def run_touch_role(state, host, chobolo_path):
    """
    Ensures the directory /tmp/ch-aronte-test exists.
    """
    add_op(
        state,
        server.dir,
        name="Ensure /tmp/ch-aronte-test directory exists",
        path="/tmp/ch-aronte-test",
        present=True,
        _sudo=True # Use sudo if necessary
    )
    run_ops(state)
```
