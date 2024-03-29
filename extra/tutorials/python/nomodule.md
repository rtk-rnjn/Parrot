If you've installed a package but you're getting a ModuleNotFoundError when you try to import it, it's likely that the environment where your code is running is different from the one where you did the installation.

Common causes of this problem include:

- You installed your package using `pip install ...`. It could be that the `pip` command is not pointing to the environment where your code runs. For greater control, you could instead run pip as a module within the python environment you specify:
```
python -m pip install <your_package>
```
- Your editor/ide is configured to create virtual environments automatically (PyCharm is configured this way by default).