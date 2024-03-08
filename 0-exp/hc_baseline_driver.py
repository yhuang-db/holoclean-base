import argparse
import time

import toml

import holoclean
from detect import *
from eval_driver import attr_evaluation
from repair.featurize import *

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--DBName")
    parser.add_argument("-t", "--Toml")
    args = parser.parse_args()

    # dbms
    db_name = args.DBName
    print(f'db_name: {db_name}')

    # toml config
    toml_file = args.Toml
    print(f'Experiment configure file: {toml_file}')
    toml_dict = toml.load(toml_file)

    exp_dataset = toml_dict['dataset']
    city = exp_dataset['city']
    dataset_name = exp_dataset['name']
    dataset_dir = exp_dataset['dir']

    dirty_file_path = f'{dataset_dir}/{dataset_name}.csv'
    constraint_file_path = f'{city}-{dataset_name}/{dataset_name}_constraints.txt'
    hc_clean_file_path = f'{dataset_dir}/{dataset_name}_clean_hc.csv'
    print(f'Dataset name: {dataset_name}')
    print(f'Dirty file: {dirty_file_path}')
    print(f'Constraint file: {constraint_file_path}')
    print(f'Clean file: {hc_clean_file_path}')

    epochs = int(exp_dataset['epochs'])
    attrs = exp_dataset['attrs']
    print(f'epochs: {epochs}')
    print(f'train_attr: {attrs}')

    # ~~ read exp arguments ~~
    start = time.perf_counter()

    hc = holoclean.HoloClean(
        db_name=db_name,
        domain_thresh_1=0.0,
        domain_thresh_2=0.01,
        weak_label_thresh=0.95,
        max_domain=10000,
        cor_strength=0.6,
        nb_cor_strength=0.8,
        verbose=True,
        timeout=5 * 60000,
        print_fw=True,
        # sparcle experiment setups
        epochs=epochs,
        train_attrs=attrs,
    ).session

    # 2. Load training data and denial constraints.
    hc.load_data(dataset_name, dirty_file_path)
    hc.load_dcs(constraint_file_path)
    hc.ds.set_constraints(hc.get_dcs())

    # 3. Detect erroneous cells using these two detectors.
    detectors = [NullDetector(), ViolationDetector()]
    hc.detect_errors(detectors)

    # 4. Repair errors utilizing the defined features.
    hc.generate_domain()
    hc.run_estimator()
    featurizers = [
        # OccurAttrFeaturizer(),
        # FreqFeaturizer(),
        ConstraintFeaturizer(),
    ]

    hc.repair_errors(featurizers)

    # 5. Evaluate the correctness of the results.
    report = hc.evaluate(fpath=hc_clean_file_path,
                         tid_col='tid',
                         attr_col='attribute',
                         val_col='correct_val')
    end = time.perf_counter()
    runtime = time.strftime("%Hh%Mm%Ss", time.gmtime(end - start))

    # 6. Attribute evaluation
    if 'evaluation' in toml_dict:
        attr_evaluation(toml_dict, city, dataset_name, runtime)
