import asyncio
from curl_cffi import AsyncSession
from .utils.constants import get_city_id_by_name
from .models import Product
from typing import List, Dict, Any, Optional
import os
from pathlib import Path


class WildberriesClient():
    def __init__(self) -> None:
        self.session = AsyncSession()

    async def get_product(self, product_id: str, dest_name: str, spp: int = 30) -> Product:
        dest = get_city_id_by_name(dest_name)
        url = f"https://card.wb.ru/cards/v4/detail?appType=2&curr=rub&dest={dest}&spp={spp}&hide_dtype=13&nm={product_id}"
        request = await self.session.get(url)
        json_response = request.json()

        if json_response.get("products") and len(json_response["products"]) > 0:
            product_data = json_response["products"][0]
            return Product(product_data)
        else:
            raise ValueError(f"Продукт с ID {product_id} не найден")

    async def close(self):
        """Закрыть сессию"""
        await self.session.close()

    async def __aenter__(self):
        """Поддержка async context manager"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Поддержка async context manager"""
        await self.close()

    async def get_product_with_images(self, product_id: str, dest_name: str,
                                      download_images: bool = False,
                                      images_folder: str = "images",
                                      image_sizes: Optional[List[str]] = None,
                                      max_images: int = 5,
                                      spp: int = 30) -> Product:
        """Получить продукт и опционально скачать его изображения

        Args:
            product_id: ID продукта
            dest_name: название города
            download_images: скачивать ли изображения
            images_folder: папка для сохранения изображений
            image_sizes: размеры изображений для скачивания
            max_images: максимальное количество изображений
            spp: параметр spp для API

        Returns:
            Объект Product
        """
        # Получаем продукт
        product = await self.get_product(product_id, dest_name, spp)

        # Скачиваем изображения если нужно
        if download_images:
            if image_sizes:
                await product.download_images_by_size(images_folder, image_sizes, max_images)
            else:
                await product.download_all_images(images_folder, max_images=max_images)

        return product

    async def download_product_images(self, product: Product,
                                      images_folder: str = "images",
                                      image_sizes: Optional[List[str]] = None,
                                      max_images: int = 10) -> Dict[str, Any]:
        """Скачать изображения для существующего продукта

        Args:
            product: объект продукта
            images_folder: папка для сохранения
            image_sizes: размеры изображений
            max_images: максимальное количество изображений

        Returns:
            Информация о скачанных файлах
        """
        results = {
            'product_id': product.id,
            'product_name': product.name,
            'downloaded_files': [],
            'download_info': {}
        }

        if image_sizes:
            # Скачиваем в разных размерах
            download_results = await product.download_images_by_size(
                images_folder, image_sizes, max_images
            )
            results['download_info'] = download_results

            # Собираем все скачанные файлы
            for size_files in download_results.values():
                results['downloaded_files'].extend(size_files)
        else:
            # Скачиваем в стандартном размере
            downloaded_files = await product.download_all_images(images_folder, max_images=max_images)
            results['downloaded_files'] = downloaded_files
            results['download_info']['default'] = downloaded_files

        return results
