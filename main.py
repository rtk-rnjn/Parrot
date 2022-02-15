from dotenv import load_dotenv, dotenv_values

load_dotenv()
dotenv_values(".env")

if __name__ == "__main__":
    from core import Parrot

    Parrot().run()
