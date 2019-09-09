from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client

from meiduo import settings


class FastDFSStorage(Storage):
    def save(self,name,content,max_length=None):
        client = Fdfs_client(settings.FDFS_LIENT_CONF)
        result = client.upload_by_vuffer(content.read())
        if result.get('Status') == 'Upload successed.':
            file_id =result.get('Remote file_id')
            return file_id
        else:
            raise Exception('上传失败')
        
