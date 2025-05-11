from pydantic import BaseModel

from ..lazy import lazy_run


class InstructionStep(BaseModel):
    step_number: int
    instruction: str


class RecipeIngredient(BaseModel):
    name: str
    quantity: str
    unit: str
    preparation: str


class Recipe(BaseModel):
    name: str
    ingredients: list[RecipeIngredient]
    instructions: list[InstructionStep]

    def __str__(self) -> str:
        s = f"\n🍳 {self.name}\n\n"

        s += "📋 食材：\n"
        for ingredient in self.ingredients:
            s += f"・{ingredient.name:<10} {ingredient.quantity:>4} {ingredient.unit} {ingredient.preparation}\n"

        s += "\n👨‍🍳 料理步驟：\n"
        for instruction in self.instructions:
            s += f"{instruction.step_number:>2}. {instruction.instruction}\n"

        s += "\n"
        return s


async def generate_recipe(text: str, fabricate: bool = False) -> str:
    if fabricate:
        recipe = await lazy_run(
            text,
            instructions="你是位專業的廚師，精通各式料理，熟悉各種食材的搭配。使用繁體中文回答，確保回答符合台灣用語習慣。",
            output_type=Recipe,
        )
        return str(recipe)
    else:
        prompt = f"""
        從文字中抽取食譜資訊，不要捏造任何資訊。抽取後翻譯成台灣繁體中文。

        文字：
        ```
        {text}
        ```
        """
        recipe = await lazy_run(
            prompt,
            output_type=Recipe,
        )
        return str(recipe)
