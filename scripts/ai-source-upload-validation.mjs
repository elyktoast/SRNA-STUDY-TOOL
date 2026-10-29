import {createHash} from 'node:crypto';
export function validateSourceUpload(bytes,title,{maxBytes=104857600}={}){
 if(!(bytes instanceof Uint8Array)||bytes.length<8) throw new TypeError('PDF bytes required');
 if(!Number.isSafeInteger(maxBytes)||maxBytes<8) throw new RangeError('invalid size limit');
 if(bytes.length>maxBytes) throw new Error('PDF exceeds upload limit');
 if(typeof title!=='string'||!title.trim()||title.trim().length>250) throw new Error('invalid title');
 if(String.fromCharCode(...bytes.subarray(0,5))!=='%PDF-') throw new Error('invalid PDF signature');
 return {title:title.trim(),fileBytes:bytes.length,mimeType:'application/pdf',sha256:createHash('sha256').update(bytes).digest('hex')};
}
