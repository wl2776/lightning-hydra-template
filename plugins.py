import zipfile
from pathlib import Path
from hydra.core.config_store import ConfigStore
from hydra.plugins.search_path_plugin import SearchPathPlugin


class ZipSearchPathPlugin(SearchPathPlugin):
    """
    Класс для добавления путей поиска конфигураций в ZIP-архив.
    Этот класс расширяет функциональность Hydra для поиска конфигураций внутри архива.
    """
    def manipulate_search_path(self, search_path):
        """Регистрация пути к ZIP-архиву."""
        root_zip_file = Path("__main__.py").parent.resolve().as_posix()
        with zipfile.ZipFile(root_zip_file, 'r') as zf:
            for file in zf.infolist():
                if file.filename.endswith('.yaml'):
                    search_path.prepend(provider=self.plugin_name(), path=f'./configs/{file.filename}', anchor=".")
