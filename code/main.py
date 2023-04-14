# -*- coding: utf-8 -*-

import os
import warnings
import multiprocessing
from pathlib import Path
import traceback

import file_system_functions as fs
from preprocessing import Preprocessing, ask_yes_no_mask, ask_yes_no_preprocessing
from processing import TimeCollector, TMapProcessor, MTProcessor, DTIProcessor
from utils import Mask, ask_user
from utils import Headermsg as hmg 

warnings.filterwarnings("ignore")


def main():
    # set the root directory
    print(hmg.welcome)
    print(f'\n{hmg.ask}Selecciona la carpeta de trabajo en la ventana emergente.')
    root_path = fs.select_directory() 
    os.chdir(root_path)

    # create the file system builder object
    fs_builder = fs.FileSystemBuilder(root_path)

    # create the folder system
    fs_builder.create_dir()

    # get studies and convert them from bruker to niftii
    fs_builder.convert_bru_to_nii() 
    
    # rename some study subfolders adding the acq method (T2,T2*,T1,D,MT,M0)
    fs_builder.rename_sutudies()
    print(f'\n{hmg.info}Se han etiquetado las carpetas de interés ' 
            'según su modalidad (T1, T2, T2star, MT, M0, D).')

    # ask user for which modalities he wants to process and 
    # replicate those studies in 'procesados'.
    fs_builder.transfer_files() 
    print(f'\n{hmg.info}Se ha creado la carpeta "procesados" y se han '
            'trasferido los archivos.')

    # select those studies to be processed
    studies_to_process, modals_to_process = fs_builder.get_selected_studies()

    if not studies_to_process:
        print(f'\n{hmg.error}No hay estudios que procesar.')
        exit()

    # get times (TR, TE and/or TE*)
    if ('T1' in modals_to_process) or \
       ('T2' in modals_to_process) or \
       ('T2E' in modals_to_process):
        time_collector = TimeCollector(root_path, 
                                        studies_to_process, 
                                        modals_to_process)
        f_time_paths = time_collector.get_times(how='auto')

    # generate parametric maps
    prev_patient_name = ""
    for study in studies_to_process: 
        study_name = study.parts[-1]
        patient_name = study.parts[-2].split("_")[1:]
        if patient_name != prev_patient_name:
            print(f'\n\n\n\n{hmg.new_patient1}{"_".join(patient_name)} {hmg.new_patient2}')
        prev_patient_name = patient_name[:]
        current_modal = study_name.split("_")[0]
        print(f'\n\n{hmg.new_modal}Procesamiento del mapa de {current_modal}')
        
        mask_path = Path('/'.join(study.parts[0:-1])) / 'mask.nii'
        if mask_path.exists(): 
            reuse_mask = ask_user('¿Deseas reutilizar la máscara creada para este sujeto?')

        if (not mask_path.exists()) or (not reuse_mask):
            mask = Mask(study)
            correct_selection = False
            while not correct_selection:
                mask.create_mask()
                correct_selection = ask_user('¿Es la previsualización de la selección lo que deseas?')
            print(f'\n{hmg.info}Máscara creada correctamente.')
        
        want_preprocess = ask_user('¿Deseas realizar un preprocesado de este estudio?')

        if study_name.startswith('DT'): 
            dti_map_pro = DTIProcessor(root_path, study)
            if want_preprocess:
                Preprocessing([study]).preprocess()
            dti_map_pro.process_DTI()
        
        elif study_name.startswith('MT'):
            mt_map_pro = MTProcessor(study, mask_path)
            if want_preprocess:
                Preprocessing([study]).preprocess()
            mt_map_pro.process_MT()

        else:
            n_cpu = multiprocessing.cpu_count() - 1
            t_map_pro = TMapProcessor(study, mask_path, n_cpu=n_cpu, fitting_mode='nonlinear') 
            if want_preprocess:
                Preprocessing([study]).preprocess()
            t_map_pro.process_T_map(f_time_paths)

    fs_builder.empty_supplfiles()
    print(f'\n{hmg.success}Procesamiento terminado.')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f'\n\n{hmg.error}Has salido del programa.')
    except OSError as err:
        # Por si no especificamos carpeta al inicio o no existe
        print(f'\n\n{hmg.error}Se ha producido el siguiente error: {err}')
    except Exception as err:
        print(f'\n\n{hmg.error}Se ha producido el siguiente error: {err}')
        print('Más información:\n')
        traceback.print_exc()