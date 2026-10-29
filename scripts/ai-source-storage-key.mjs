import {randomUUID} from 'node:crypto';
export function createSourceStorageKey(){
 return 'documents/'+randomUUID()+'.pdf';
}
