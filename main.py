import asyncio
from api.main import WildberriesClient


async def main():
    wb = WildberriesClient()

    try:
        # Получаем продукт
        product = await wb.get_product("241779009", "Казань")

        # Теперь у нас есть объект Product с дополнительными методами
        print("=== Информация о продукте ===")
        print(f"Название: {product.name}")
        print(f"Бренд: {product.brand}")
        print(f"Цена: {product.get_price()} руб.")

        discount = product.get_discount_percent()
        if discount:
            print(f"Скидка: {discount}%")
            print(f"Цена без скидки: {product.get_discounted_price()} руб.")

        print(f"Рейтинг: {product.rating}")
        print(f"Отзывы: {product.reviews_count}")
        print(f"Доступен: {product.is_available()}")
        print(f"Остаток: {product.get_total_stock()} шт.")
        print(f"URL: {product.get_product_url()}")

        available_sizes = product.get_available_sizes()
        if available_sizes:
            print(f"Размеры: {', '.join(available_sizes)}")

        print(f"Изображение: {product.get_main_image_url()}")

    except Exception as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())
