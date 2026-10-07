import {pocConfig} from './poc'

export function getConfig(environment: string){
    switch (environment){
        case 'poc':
            return pocConfig;
        default:
            throw new Error(
                `Unknown environment: ${environment}`
            );
    }
}