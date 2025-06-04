import sys
import os
import zipfile
import tempfile

import hydra
from hydra.core.plugins import Plugins
from hydra.core.config_search_path import ConfigSearchPath
from hydra.plugins.search_path_plugin import SearchPathPlugin

from src.train import main


def extract_configs_from_zip(zip_file_path):
    """
    Извлекает конфигурационные файлы из архива и временно сохраняет их на диск.
    Возвращает временный каталог с извлечёнными файлами.
    """
    temp_dir = tempfile.mkdtemp(prefix="hydra_extracted_")
    
    with zipfile.ZipFile(zip_file_path, 'r') as zf:
        for file in zf.infolist():
            if file.filename.startswith('configs/'):
                arcname = file.filename
                
                # Разделяем имя файла и родителя
                parts = arcname.split('/')
                basename = parts[-1]
                dir_parts = parts[:-1]
                
                # Формируем целевой путь
                fullpath = os.path.join(temp_dir, *dir_parts, basename)
                
                # Создаем промежуточные каталоги
                parent_dir = os.path.dirname(fullpath)
                if not os.path.exists(parent_dir):
                    os.makedirs(parent_dir)
                
                # Открываем файл и записываем данные
                if not file.is_dir():  # проверяем, что это не каталог
                    with open(fullpath, 'wb') as outfile:
                        outfile.write(zf.read(arcname))        
    return temp_dir


zip_file_path = sys.argv[0]
cli_args = sys.argv[1:]
extracted_temp_dir = extract_configs_from_zip(zip_file_path)

class TmpDirSearchPathPlugin(SearchPathPlugin):
    def manipulate_search_path(self, search_path: ConfigSearchPath) -> None:
        search_path.append(
            provider="tmpdir-searchpath-plugin", path=extracted_temp_dir
        )


try:
    Plugins.instance().register(TmpDirSearchPathPlugin)
    
    hydra.initialize(config_path="./configs", version_base='1.3')
    cfg = hydra.compose(config_name="train.yaml", overrides=cli_args)

    main(cfg)
finally:
    pass
    # import shutil
    # shutil.rmtree(extracted_temp_dir) == "__main__":
