import asyncio

from aiogram import types, Dispatcher

import random
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram import filters, Router
from aiogram.fsm.state import State, StatesGroup

from googletrans import Translator
from aiohttp import ClientSession


MEALDB_API_BASE_URL = "https://www.themealdb.com/api/json/v1/1"

translator = Translator()
router = Router()

class FSM(StatesGroup):
    waiting_for_category = State()
    waiting_for_confirmation = State()

@router.message(Command("category_search_random"))
async def category_search_random_command(message: types.Message, state: FSMContext):
    if not message.text:
        return
    count = int(message.text.split()[1])
    category = message.text.split()[2]
    await state.set_data({"count": count, "category": category})

    async with ClientSession() as session:
        response = await session.get(f"{MEALDB_API_BASE_URL}/list.php?c=list")
        categories = await response.json()

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    for category in categories["meals"]:
        markup.add(KeyboardButton(category["strCategory"]))

    await message.answer("Выберите категорию:", reply_markup=markup)
    await state.set_state(FSM.waiting_for_category.state)

@router.message(FSM.waiting_for_category)
async def category_search_button_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    count = data["count"]
    category = message.text

    async with ClientSession() as session:
        response = await session.get(f"{MEALDB_API_BASE_URL}/filter.php?c={category}")
        meals = await response.json()

    random_recipes = random.choices(meals["meals"], k=count)
    recipe_ids = [meal["idMeal"] for meal in random_recipes]

    await state.set_data({"recipe_ids": recipe_ids})

    for meal in random_recipes:
        translated_title = translator.translate(meal["strMeal"], dest="ru").text
        await message.answer(translated_title)

    await message.answer("Показать рецепты?", reply_markup=types.ReplyKeyboardMarkup(text='Покажи рецепты'))
    await state.set_state(FSM.waiting_for_confirmation.state)

@router.message(FSM.waiting_for_confirmation)
async def get_recipe_by_id_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    recipe_ids = data["recipe_ids"]

    if message.text == "Да":
        for recipe_id in recipe_ids:
            async with ClientSession() as session:
                response = await session.get(f"{MEALDB_API_BASE_URL}/lookup.php?i={recipe_id}")
                meal = await response.json()

            translated_title = translator.translate(meal["meals"][0]["strMeal"], dest="ru").text
            translated_recipe = translator.translate(meal["meals"][0]["strInstructions"], dest="ru").text
            ingredients = meal["meals"][0]["strIngredients"].split(",")

            await message.answer(f"**{translated_title}**")
            await message.answer(f"**Рецепт:**\n{translated_recipe}")
            await message.answer(f"**Ингредиенты:**\n{', '.join(ingredients)}")

    await state.finish()

