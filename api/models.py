from typing import List, Optional, Dict, Any
import os
import asyncio
import aiohttp
from pathlib import Path
from .utils.constants import get_warehouse_name_by_id, is_seller_warehouse, is_wb_warehouse


class Product:
    def __init__(self, product_data: Dict[str, Any]):
        self.raw_data = product_data
        self.id = product_data.get('id')
        self.root = product_data.get('root')
        self.name = product_data.get('name', '')
        self.brand = product_data.get('brand', '')
        self.brand_id = product_data.get('brandId')
        self.entity = product_data.get('entity', '')
        self.supplier = product_data.get('supplier', '')
        self.supplier_id = product_data.get('supplierId')
        self.supplier_rating = product_data.get('supplierRating', 0)
        self.rating = product_data.get('rating', 0)
        self.review_rating = product_data.get('reviewRating', 0)
        self.nm_review_rating = product_data.get('nmReviewRating', 0)
        self.feedbacks = product_data.get('feedbacks', 0)
        self.nm_feedbacks = product_data.get('nmFeedbacks', 0)
        self.sizes = product_data.get('sizes', [])
        self.colors = product_data.get('colors', [])
        self.pics = product_data.get('pics', 0)  # Это число, а не массив
        self.volume = product_data.get('volume', 0)
        self.promotions = product_data.get('promotions', [])
        self.total_quantity = product_data.get('totalQuantity', 0)

    def get_price(self) -> Optional[float]:
        """Получить текущую цену продукта (цена со скидкой)"""
        if self.sizes and len(self.sizes) > 0:
            price_data = self.sizes[0].get('price', {})
            product_price = price_data.get('product', 0)
            return product_price / 100 if product_price else None
        return None

    def get_basic_price(self) -> Optional[float]:
        """Получить базовую цену без скидки"""
        if self.sizes and len(self.sizes) > 0:
            price_data = self.sizes[0].get('price', {})
            basic_price = price_data.get('basic', 0)
            return basic_price / 100 if basic_price else None
        return None

    def get_logistics_price(self) -> Optional[float]:
        """Получить стоимость логистики"""
        if self.sizes and len(self.sizes) > 0:
            price_data = self.sizes[0].get('price', {})
            logistics_price = price_data.get('logistics', 0)
            return logistics_price / 100 if logistics_price else None
        return None

    def get_discount_percent(self) -> Optional[int]:
        """Получить процент скидки"""
        basic_price = self.get_basic_price()
        current_price = self.get_price()

        if basic_price and current_price and basic_price > current_price:
            discount = ((basic_price - current_price) / basic_price) * 100
            return round(discount)
        return None

    def get_available_colors(self) -> List[str]:
        """Получить доступные цвета"""
        return [color.get('name', '') for color in self.colors if color.get('name')]

    def get_color_ids(self) -> List[int]:
        """Получить ID цветов"""
        return [color.get('id', 0) for color in self.colors if color.get('id')]

    def get_available_sizes(self) -> List[str]:
        """Получить доступные размеры"""
        available_sizes = []
        for size in self.sizes:
            stocks = size.get('stocks', [])
            if any(stock.get('qty', 0) > 0 for stock in stocks):
                size_name = size.get('name', size.get('origName', ''))
                if size_name and size_name != '0':
                    available_sizes.append(size_name)
        return available_sizes

    def get_warehouse_info(self) -> List[Dict[str, Any]]:
        """Получить информацию о складах и остатках"""
        warehouse_info = []
        for size in self.sizes:
            stocks = size.get('stocks', [])
            for stock in stocks:
                warehouse_id = stock.get('wh')
                warehouse_info.append({
                    'warehouse_id': warehouse_id,
                    'warehouse_name': get_warehouse_name_by_id(warehouse_id),
                    'is_seller_warehouse': is_seller_warehouse(warehouse_id),
                    'is_wb_warehouse': is_wb_warehouse(warehouse_id),
                    'quantity': stock.get('qty', 0),
                    'delivery_time_1': stock.get('time1', 0),
                    'delivery_time_2': stock.get('time2', 0),
                    'distance': stock.get('dist', 0),
                    'priority': stock.get('priority', 0)
                })
        return warehouse_info

    def get_wb_warehouses_info(self) -> List[Dict[str, Any]]:
        """Получить информацию только о складах Wildberries"""
        return [wh for wh in self.get_warehouse_info() if wh['is_wb_warehouse']]

    def get_seller_warehouses_info(self) -> List[Dict[str, Any]]:
        """Получить информацию только о складах продавцов"""
        return [wh for wh in self.get_warehouse_info() if wh['is_seller_warehouse']]

    def get_total_wb_stock(self) -> int:
        """Получить общее количество товара на складах Wildberries"""
        return sum(wh['quantity'] for wh in self.get_wb_warehouses_info())

    def get_total_seller_stock(self) -> int:
        """Получить общее количество товара на складах продавцов"""
        return sum(wh['quantity'] for wh in self.get_seller_warehouses_info())

    def get_warehouses_summary(self) -> Dict[str, Any]:
        """Получить сводную информацию о складах"""
        wb_warehouses = self.get_wb_warehouses_info()
        seller_warehouses = self.get_seller_warehouses_info()

        return {
            'total_warehouses': len(wb_warehouses) + len(seller_warehouses),
            'wb_warehouses_count': len(wb_warehouses),
            'seller_warehouses_count': len(seller_warehouses),
            'total_wb_stock': self.get_total_wb_stock(),
            'total_seller_stock': self.get_total_seller_stock(),
            'wb_warehouses': wb_warehouses,
            'seller_warehouses': seller_warehouses
        }

    def get_main_image_url(self, size: str = 'c516x688') -> Optional[str]:
        """Получить URL основного изображения

        Args:
            size: размер изображения (например: 'c516x688', 'tm', 'big')
        """
        if self.pics and self.pics > 0 and self.id:
            # Определяем номер корзины на основе id (актуальный алгоритм)
            id_str = str(self.id)

            # Более точный алгоритм определения корзины
            if self.id <= 143:
                basket = "01"
            elif self.id <= 287:
                basket = "02"
            elif self.id <= 431:
                basket = "03"
            elif self.id <= 719:
                basket = "04"
            elif self.id <= 1007:
                basket = "05"
            elif self.id <= 1061:
                basket = "06"
            elif self.id <= 1115:
                basket = "07"
            elif self.id <= 1169:
                basket = "08"
            elif self.id <= 1313:
                basket = "09"
            elif self.id <= 1601:
                basket = "10"
            elif self.id <= 1655:
                basket = "11"
            elif self.id <= 1919:
                basket = "12"
            elif self.id <= 2045:
                basket = "13"
            elif self.id <= 2189:
                basket = "14"
            elif self.id <= 2405:
                basket = "15"
            else:
                basket = "16"  # Для больших ID используется basket-16

            # Определяем vol и part
            vol = int(id_str[:-5]) if len(id_str) > 5 else 0
            part = int(id_str[:-3]) if len(id_str) > 3 else self.id

            return f"https://basket-{basket}.wbbasket.ru/vol{vol}/part{part}/{self.id}/images/{size}/1.webp"
        return None

    def get_all_images_urls(self, size: str = 'c516x688') -> List[str]:
        """Получить URLs всех изображений"""
        image_urls = []
        if self.pics and self.pics > 0 and self.id:
            # Определяем номер корзины на основе id
            id_str = str(self.id)
            if self.id <= 143:
                basket = "01"
            elif self.id <= 287:
                basket = "02"
            elif self.id <= 431:
                basket = "03"
            elif self.id <= 719:
                basket = "04"
            elif self.id <= 1007:
                basket = "05"
            elif self.id <= 1061:
                basket = "06"
            elif self.id <= 1115:
                basket = "07"
            elif self.id <= 1169:
                basket = "08"
            elif self.id <= 1313:
                basket = "09"
            elif self.id <= 1601:
                basket = "10"
            elif self.id <= 1655:
                basket = "11"
            elif self.id <= 1919:
                basket = "12"
            elif self.id <= 2045:
                basket = "13"
            elif self.id <= 2189:
                basket = "14"
            elif self.id <= 2405:
                basket = "15"
            else:
                basket = "16"  # Для больших ID используется basket-16

            # Определяем vol и part
            vol = int(id_str[:-5]) if len(id_str) > 5 else 0
            part = int(id_str[:-3]) if len(id_str) > 3 else self.id

            for i in range(1, min(self.pics + 1, 15)):  # Обычно не больше 15 фото
                url = f"https://basket-{basket}.wbbasket.ru/vol{vol}/part{part}/{self.id}/images/{size}/{i}.webp"
                image_urls.append(url)
        return image_urls

    def is_available(self) -> bool:
        """Проверить, доступен ли товар"""
        return self.total_quantity > 0

    def get_total_stock(self) -> int:
        """Получить общее количество товара на складах"""
        return self.total_quantity

    def get_delivery_info(self) -> Dict[str, int]:
        """Получить информацию о доставке"""
        if self.sizes and len(self.sizes) > 0:
            return {
                'time1': self.sizes[0].get('time1', 0),
                'time2': self.sizes[0].get('time2', 0),
                'distance': self.sizes[0].get('dist', 0)
            }
        return {'time1': 0, 'time2': 0, 'distance': 0}

    def has_promotions(self) -> bool:
        """Проверить, есть ли акции на товар"""
        return len(self.promotions) > 0

    def get_promotions(self) -> List[int]:
        """Получить список ID акций"""
        return self.promotions

    def get_product_url(self) -> str:
        """Получить URL товара на Wildberries"""
        if self.id:
            return f"https://www.wildberries.ru/catalog/{self.id}/detail.aspx"
        return ""

    def get_supplier_info(self) -> Dict[str, Any]:
        """Получить информацию о поставщике"""
        return {
            'name': self.supplier,
            'id': self.supplier_id,
            'rating': self.supplier_rating
        }

    def __str__(self) -> str:
        price = self.get_price()
        price_str = f"{price} руб." if price else "Цена не указана"
        return f"{self.name} ({self.brand}) - {price_str}"

    def __repr__(self) -> str:
        return f"Product(id={self.id}, name='{self.name}', brand='{self.brand}', price={self.get_price()})"

    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать объект в словарь с основной информацией"""
        return {
            'id': self.id,
            'root': self.root,
            'name': self.name,
            'brand': self.brand,
            'brand_id': self.brand_id,
            'entity': self.entity,
            'supplier': self.supplier,
            'supplier_info': self.get_supplier_info(),
            'rating': self.rating,
            'review_rating': self.review_rating,
            'nm_review_rating': self.nm_review_rating,
            'feedbacks': self.feedbacks,
            'nm_feedbacks': self.nm_feedbacks,
            'price': self.get_price(),
            'basic_price': self.get_basic_price(),
            'logistics_price': self.get_logistics_price(),
            'discount_percent': self.get_discount_percent(),
            'available_colors': self.get_available_colors(),
            'available_sizes': self.get_available_sizes(),
            'main_image_url': self.get_main_image_url(),
            'product_url': self.get_product_url(),
            'is_available': self.is_available(),
            'total_stock': self.get_total_stock(),
            'delivery_info': self.get_delivery_info(),
            'has_promotions': self.has_promotions(),
            'promotions': self.get_promotions(),
            'volume': self.volume,
            'pics_count': self.pics,
            'warehouses_summary': self.get_warehouses_summary()
        }

    async def download_main_image(self, folder_path: str = "images", image_size: str = "c516x688") -> Optional[str]:
        """Скачать основное изображение товара

        Args:
            folder_path: путь к папке для сохранения
            image_size: размер изображения

        Returns:
            Путь к скачанному файлу или None если скачивание не удалось
        """
        main_image_url = self.get_main_image_url(image_size)
        if not main_image_url:
            return None

        # Создаем папку если её нет
        Path(folder_path).mkdir(parents=True, exist_ok=True)

        # Формируем имя файла
        filename = f"{self.id}_main.webp"
        file_path = os.path.join(folder_path, filename)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(main_image_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(file_path, 'wb') as f:
                            f.write(content)
                        return file_path
        except Exception as e:
            print(f"Ошибка при скачивании изображения {main_image_url}: {e}")
            return None

        return None

    async def download_all_images(self, folder_path: str = "images", image_size: str = "c516x688", max_images: int = 10) -> List[str]:
        """Скачать все изображения товара

        Args:
            folder_path: путь к папке для сохранения
            image_size: размер изображения
            max_images: максимальное количество изображений для скачивания

        Returns:
            Список путей к скачанным файлам
        """
        image_urls = self.get_all_images_urls(image_size)[:max_images]

        if not image_urls:
            return []

        # Создаем папку если её нет
        Path(folder_path).mkdir(parents=True, exist_ok=True)

        downloaded_files = []

        async with aiohttp.ClientSession() as session:
            tasks = []
            for i, url in enumerate(image_urls, 1):
                filename = f"{self.id}_{i}.webp"
                file_path = os.path.join(folder_path, filename)
                tasks.append(self._download_single_image(
                    session, url, file_path))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, str) and result:  # Успешно скачанный файл
                    downloaded_files.append(result)
                elif isinstance(result, Exception):
                    print(f"Ошибка при скачивании: {result}")

        return downloaded_files

    async def _download_single_image(self, session: aiohttp.ClientSession, url: str, file_path: str) -> Optional[str]:
        """Скачать одно изображение

        Args:
            session: aiohttp сессия
            url: URL изображения
            file_path: путь для сохранения файла

        Returns:
            Путь к скачанному файлу или None
        """
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    return file_path
        except Exception as e:
            print(f"Ошибка при скачивании изображения {url}: {e}")
            return None

        return None

    async def download_images_by_size(self, folder_path: str = "images", sizes: Optional[List[str]] = None, max_images: int = 5) -> Dict[str, List[str]]:
        """Скачать изображения в разных размерах

        Args:
            folder_path: путь к папке для сохранения
            sizes: список размеров изображений
            max_images: максимальное количество изображений для каждого размера

        Returns:
            Словарь с размерами и списками путей к скачанным файлам
        """
        if sizes is None:
            sizes = ['tm', 'c246x328', 'c516x688', 'big']

        results = {}

        for size in sizes:
            size_folder = os.path.join(folder_path, size)
            downloaded = await self.download_all_images(size_folder, size, max_images)
            results[size] = downloaded

        return results
