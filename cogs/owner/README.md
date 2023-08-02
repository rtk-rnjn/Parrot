# wikihow.py

A simple wikihow.com API/scraper for Python 3.10+ for my discord bot.

## Usage

```py
from wikihow import Parser

async def main():
    parser = Parser()
    await parser.init()

    article: list[tuple[str, str, int]] = await parser.get_wikihow("How to Make a Pizza")
    # list[tuple["title", "snippet", page_id]]
    print(article)

    page: dict = await parser.get_wikihow_article(article[0][2])
    print(page)

    await parser.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

## Page Structure

```py

page = {
    "title": "Make Pepperoni Pizza",
    "real": {
        "intro": "When it comes to pizza toppings, pepperoni is definitely a classic...",
        "Ingredients": {
            "Dough": [
                "\u00bd cup (118 ml) warm water, about 110 degrees F (43 degrees Celsius)",
                "1 envelope instant yeast",
                ...
            ],
            "Sauce": [
                "2 tablespoons (30 ml) olive oil",
                "2 cloves garlic, minced",
                ...
            ],
            ...
        },
        "Steps": {
            "Making the Dough": [
                "Combine the warm water and yeast...",
                [
                    "Your warm water should be approximately 110 degrees Fahrenheit (43 degrees Celsius).",
                    ...
                ],
                "Add the room temperature water and oil...",
                [
                    "Room temperature water should be approximately 75 degrees Fahrenheit (24 degrees Celsius).",
                    ...
                ],
                ...
            ],
            "Preparing the Sauce": [...],
            ...: [...],
            ...: [...],
        },
        "Video": {},
        "Tips": {
            "sub_head_list_{N}": "Feel free to add other toppings to the pizza with the pepperoni..."
        },
        "Things You'll Need": {
            "sub_head_list_{N}": "Small bowl\nFood processor\nLarge bowl..."
        },
        "Related wikiHows": {
            "sub_head_list_{N}": "Make Pepperoni Pizza\nBake a Totino's Party Pizza..."
        },
        "References": {
            "sub_head_list_{N}": "Videos provided by Crouton Crackerjacks...",
            "sub_head_div_list_1": [
                "\u2191 http://www.browneyedbaker.com/pepperoni-pizza/",
                "\u2191 http://www.browneyedbaker.com/pepperoni-pizza/",
                ...
            ]
        },
        "Quick Summary": {
            "sub_head_para_{N}": "To make homemade pepperoni pizza, combine \u00bd cup (118 mL) ..."
        }
    }
}

N: int
```
