import {createHash} from 'node:crypto';
export function assertSourceChecksum(bytes,expected){
 if(!(bytes instanceof Uint8Array)) throw new TypeError('PDF bytes required');
 if(typeof expected!=='string'||expected.length!==64) throw new Error('invalid source checksum');
 const actual=createHash('sha256').update(bytes).digest('hex');
 if(actual!==expected.toLowerCase()) throw new Error('source checksum mismatch');
 return true;
}
