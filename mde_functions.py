import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from scipy.stats import ttest_ind
import datetime


def plot_pvalue_distribution(dict_pvalues, legend_list, alphas):
    """Рисует графики распределения p-value."""
    X = np.linspace(0, 1, 1000)
    for pvalues in dict_pvalues:
        Y = [np.mean(pvalues < x) for x in X]
        plt.plot(X, Y)
    plt.plot([0, 1], [0, 1], '--k', alpha=0.8)
    for alpha in alphas:
        plt.axvline(x=alpha, color='grey', linewidth=0.5, linestyle='dashed')
    plt.title('Оценка распределения p-value', size=16)
    plt.xlabel('p-value', size=12)
    plt.legend(legend_list)
    plt.grid()

    
def add_0(x):
    s = str(x)
    return '0' * (3 - len(s)) + s

    
def print2(x):
    x = int(x)
    a = []
    while x > 1000:
        a.append(add_0(x % 1000))
        x = x // 1000
    a.append(str(x))
    print(','.join(reversed(a)))


def regional_test(result, metric, unit, days, effects, alpha = 0.05, alternative='two-sided', n_runs=10000):
    legend_list = ['random', f'alpha={alpha * 100}%']
    global_list = []
    start_date = pd.to_datetime(result['start_dt'].min())
    end_date =  pd.to_datetime(result['start_dt'].max())
    unq = result['region_id'].unique()
    dates = rng = pd.date_range(start_date, pd.Timestamp(end_date) - pd.Timedelta(days=days - 1))
    for effect in effects:
        new_list = []
        for i in range(n_runs):
            d = np.random.choice(rng)
            res = result[(result['start_dt'] >= d) & (result['start_dt'] <= d + pd.Timedelta(days=days - 1))]
            reg_4_test = unq

            # Выбираем случайные регионы в тест и контроль
            test_regions = np.random.choice(reg_4_test, int(len(reg_4_test) / 2), replace=False)
            control_regions = list(set(reg_4_test) - set(test_regions))

            # Разметка групп
            df.index = np.where(
                (df['region_id'].isin(test_regions)),
                'test', 'control'
            ) 
            df.loc['test', metric] *= effect

            # Линеаризация метрики  
            CNTRL_ratio = df.loc['control', metric].sum() / df.loc['control', unit].sum()
            df['linearized_metric'] = df[metric] - df[unit] * CNTRL_ratio

            # t-test
            control = df.loc['control', 'linearized_metric']
            test = df.loc['test', 'linearized_metric']
            new_list.append(ttest_ind(test, control, alternative=alternative).pvalue)
            
        # Анализ результатов
        p_val_frame = pd.DataFrame(new_list, columns=['p_val'])
        if effect == 1:
            legend_list.append('A/A')
            print(
                'Ошибка 1 рода:', 
                np.sum(p_val_frame.p_val < alpha) / p_val_frame.shape[0])
        else:
            legend_list.append(f'lift {round(100*(effect-1.0),2)}%')
            print(
                f'{round(100 * (effect - 1), 2)}% uplift:',
                f'{(1 - np.sum(p_val_frame.p_val >= alpha) / p_val_frame.shape[0]) * 100}% мощность'
            )
        global_list.append(new_list)  
    plot_pvalue_distribution(global_list, legend_list, alpha)


def w_calculate(X, X_pre): # X - данные на текущем периоде, X_pre - данные на пред периоде (к которым мы "приводим")
    X = np.array(X)
    X_pre = np.array(X_pre)
    w = np.cov(X, X_pre)[0, 1] / X_pre.var() # считаем ковариату
    return w


def cuped(X, X_pre, w = 0, E = None):
    if w == 0:
        w = w_calculate(X, X_pre)
    X = np.array(X)
    X_pre = np.array(X_pre)
    if E is None:
        E = X_pre.mean()
    X_cuped = X - w * X_pre + w * E
    return X_cuped

    
def switchback(result, metric, unit, days, effects, alpha = 0.05, alternative='two-sided', n_runs=10000):
    legend_list = ['random', f'alpha={alpha * 100}%']
    global_list = []
    start_date = pd.to_datetime(result['start_dt'].min())
    end_date =  pd.to_datetime(result['start_dt'].max())
    step = datetime.timedelta(days=2)  # Шаг в один день
    test_dates = []
    control_dates = []
    current_date = start_date
    while current_date <= end_date:
        test_dates.append(current_date)
        control_dates.append(current_date + datetime.timedelta(days=1))
        current_date += step
        
    unq = result['region_id'].unique()
    dates = rng = pd.date_range(start_date, pd.Timestamp(end_date) - pd.Timedelta(days=days - 1))
    
    for effect in effects:
        new_list = []
        for i in range(n_runs):
            d = np.random.choice(rng)
            res = result[(result['start_dt'] >= d) & (result['start_dt'] <= d + pd.Timedelta(days=days - 1))]
            reg_4_test = unq

            # Выбираем случайные регионы в тест и контроль
            test_regions = np.random.choice(reg_4_test, int(len(reg_4_test) / 2), replace=False)
            control_regions = list(set(reg_4_test) - set(test_regions))

            # Разметка групп
            df.index = np.where(
                (df['region_id'].isin(test_regions)) & (df['start_dt'].isin(test_dates)) |
                (df['region_id'].isin(control_regions)) & (df['start_dt'].isin(control_dates)),
                'test', 'control'
            ) 
            df.loc['test', metric] *= effect

            # Линеаризация метрики  
            CNTRL_ratio = df.loc['control', metric].sum() / df.loc['control', unit].sum()
            df['linearized_metric'] = df[metric] - df[unit] * CNTRL_ratio

            # t-test
            control = df.loc['control', 'linearized_metric']
            test = df.loc['test', 'linearized_metric']
            new_list.append(ttest_ind(test, control, alternative=alternative).pvalue)
            
        # Анализ результатов
        p_val_frame = pd.DataFrame(new_list, columns=['p_val'])
        if effect == 1:
            legend_list.append('A/A')
            print(
                'Ошибка 1 рода:', 
                np.sum(p_val_frame.p_val < alpha) / p_val_frame.shape[0])
        else:
            legend_list.append(f'lift {round(100*(effect-1.0),2)}%')
            print(
                f'{round(100 * (effect - 1), 2)}% uplift:',
                f'{(1 - np.sum(p_val_frame.p_val >= alpha) / p_val_frame.shape[0]) * 100}% мощность'
            )
        global_list.append(new_list)  
    plot_pvalue_distribution(global_list, legend_list, alpha)



def switchback_cuped(result, result_pre, metric, unit, days, effects, alphas=[0.01, 0.0125, 0.0167, 0.025, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5], alternative='greater', n_runs=10000):
    start_date = pd.to_datetime(result['start_dt'].min())  # Начальная дата
    end_date =  pd.to_datetime(result['start_dt'].max())  # Конечная дата
    step = datetime.timedelta(days=2)  # Шаг в один день
    test_dates = []
    control_dates = []
    current_date = start_date
    while current_date <= end_date:
        test_dates.append(current_date)
        control_dates.append(current_date + datetime.timedelta(days=1))
        current_date += step
    
    start_dt = result['start_dt'].min()
    end_dt = result['start_dt'].max()

    legend_list = []
    metric_pre = metric + '_pre'
    unit_pre = unit + '_pre'
    global_list = []
    unq = result['region_id'].unique()
    dates = rng = pd.date_range(start_date, pd.Timestamp(end_date) - pd.Timedelta(days=days - 1))
    for effect in sorted(effects):
        new_list = []
        for i in range(n_runs):
            d = np.random.choice(rng)
            res = result[(result['start_dt'] >= d) & (result['start_dt'] <= d + pd.Timedelta(days=days - 1))]
            
            # Добавить данные, полученные до эксперимента
            res = res.merge(result_pre[result_pre['exp_start_dt'] == d], on=['region_id', 'weekday'], how='left')
            # Заменить пропуски в unit_pre на среднее значение для данного региона
            res.loc[res[res['exp_start_dt'].isna()].index, unit_pre] = np.array(res[res['exp_start_dt'].isna()].merge(res[res['region_id'].isin(res[res['exp_start_dt'].isna()]['region_id'].unique())].groupby('region_id', as_index=False).agg({unit: 'mean'}), on='region_id', suffixes=['', '_avg'])[unit + '_avg'])
            # Заменить пропуски в metric_pre на unit_pre * sum(metric_pre) / sum(unit_pre)
            res.loc[res[res['exp_start_dt'].isna()].index, metric_pre] = res[res['exp_start_dt'].isna()][unit_pre] * (res[metric_pre].sum() / res[unit_pre].sum())
            reg_4_test = unq

            # Выбираем случайные регионы в тест и контроль
            test_regions = np.random.choice(reg_4_test, int(len(reg_4_test) / 2), replace=False)
            control_regions = list(set(reg_4_test) - set(test_regions))

            # Разметка групп
            df.index = np.where(
                (df['region_id'].isin(test_regions)) & (df['start_dt'].isin(test_dates)) |
                (df['region_id'].isin(control_regions)) & (df['start_dt'].isin(control_dates)),
                'test', 'control'
            )
            df.loc['test', metric] *= effect

            # Линеаризация метрики
            CNTRL_ratio = df.loc['control', metric].sum() / df.loc['control', unit].sum()
            df['linearized_metric'] = df[metric] - df[unit] * CNTRL_ratio
            CNTRL_ratio_pre = df.loc['control', metric_pre].sum() / df.loc['control', unit_pre].sum()
            df['linearized_metric_pre'] = df[metric_pre] - df[unit_pre] * CNTRL_ratio_pre

            # CUPED + t-test
            control = df.loc['control']
            test = df.loc['test']   

            
            control_cuped = cuped(control['linearized_metric'], control['linearized_metric_pre'])
            test_cuped = cuped(test['linearized_metric'], test['linearized_metric_pre'])

            new_list.append(ttest_ind(test_cuped, control_cuped, alternative=alternative).pvalue)       

        # Анализ результатов
        p_val_frame = pd.DataFrame(new_list, columns=['p_val'])
        if effect == 1:
            legend_list.append('A/A')
            p_vals = [str(round(100 * (np.sum(p_val_frame.p_val < alpha).item() / p_val_frame.shape[0]), 2)) + '%' for alpha in alphas]
            print('Ошибки 1 рода:', ', '.join(p_vals[:alphas.index(0.05) + 1]), '|||', ', '.join(p_vals[alphas.index(0.05) + 1:]))
        else:
            legend_list.append(f'lift {round(100*(effect-1.0),2)}%')
            p_vals = [str(round(100*((1 - np.sum(p_val_frame.p_val >= alpha) / p_val_frame.shape[0])), 2)) + '%' for alpha in alphas]
            print(f'{round(100 * (effect - 1), 2)}% uplift:', ', '.join(p_vals[:alphas.index(0.05) + 1]), '|||', ', '.join(p_vals[alphas.index(0.05) + 1:]))
        global_list.append(new_list)  
    plot_pvalue_distribution(global_list, legend_list, [0.05])
    return global_list, legend_list


def cumped(X, X_pre, w=0, E=None):
    X = np.asarray(X, dtype=float).reshape(-1)
    X_pre = np.asarray(pd.DataFrame(X_pre), dtype=float)

    if X_pre.shape[0] != X.shape[0]:
        raise ValueError('X and X_pre must have the same number of rows')

    if E is None:
        E = np.nanmean(X_pre, axis=0)

    E = np.asarray(E, dtype=float).reshape(-1)
    E = np.where(np.isfinite(E), E, 0.0)

    # Missing covariate values are centered to zero contribution.
    X_pre_filled = np.where(np.isfinite(X_pre), X_pre, E)
    X_pre_centered = X_pre_filled - E

    if w is None or (np.isscalar(w) and w == 0):
        valid_rows = np.isfinite(X) & np.all(np.isfinite(X_pre_centered), axis=1)
        if valid_rows.sum() == 0 or X_pre_centered.shape[1] == 0:
            w = np.zeros(X_pre_centered.shape[1])
        else:
            X_centered = X[valid_rows] - np.nanmean(X[valid_rows])
            covariates_centered = X_pre_centered[valid_rows]
            w = np.linalg.pinv(covariates_centered.T @ covariates_centered) @ covariates_centered.T @ X_centered

    w = np.asarray(w, dtype=float).reshape(-1)
    X_cumped = X - X_pre_centered @ w
    return X_cumped


def switchback_cumped(result, result_pre, metric, unit, days, effects, alphas=[0.01, 0.0125, 0.0167, 0.025, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5], alternative='greater', n_runs=10000, additional_covariats=[]):
    start_date = pd.to_datetime(result['start_dt'].min())  # Начальная дата
    end_date =  pd.to_datetime(result['start_dt'].max())  # Конечная дата
    step = datetime.timedelta(days=2)  # Шаг в один день
    test_dates = []
    control_dates = []
    current_date = start_date
    while current_date <= end_date:
        test_dates.append(current_date)
        control_dates.append(current_date + datetime.timedelta(days=1))
        current_date += step
    
    start_dt = result['start_dt'].min()
    end_dt = result['start_dt'].max()

    legend_list = []
    metric_pre = metric + '_pre'
    unit_pre = unit + '_pre'
    global_list = []
    unq = result['region_id'].unique()
    dates = rng = pd.date_range(start_date, pd.Timestamp(end_date) - pd.Timedelta(days=days - 1))
    for effect in sorted(effects):
        new_list = []
        for i in range(n_runs):
            d = np.random.choice(rng)
            res = result[(result['start_dt'] >= d) & (result['start_dt'] <= d + pd.Timedelta(days=days - 1))]
            
            # Добавить данные, полученные до эксперимента
            res = res.merge(result_pre[result_pre['exp_start_dt'] == d], on=['region_id', 'weekday'], how='left')

            # Заменить пропуски в unit_pre на среднее значение для данного региона
            res.loc[res[res['exp_start_dt'].isna()].index, unit_pre] = np.array(res[res['exp_start_dt'].isna()].merge(res[res['region_id'].isin(res[res['exp_start_dt'].isna()]['region_id'].unique())].groupby('region_id', as_index=False).agg({unit: 'mean'}), on='region_id', suffixes=['', '_avg'])[unit + '_avg'])
            # Заменить пропуски в metric_pre на unit_pre * sum(metric_pre) / sum(unit_pre)
            res.loc[res[res['exp_start_dt'].isna()].index, metric_pre] = res[res['exp_start_dt'].isna()][unit_pre] * (res[metric_pre].sum() / res[unit_pre].sum())
            reg_4_test = unq

            # Выбираем случайные регионы в тест и контроль
            test_regions = np.random.choice(reg_4_test, int(len(reg_4_test) / 2), replace=False)
            control_regions = list(set(reg_4_test) - set(test_regions))

            # Разметка групп
            df.index = np.where(
                (df['region_id'].isin(test_regions)) & (df['start_dt'].isin(test_dates)) |
                (df['region_id'].isin(control_regions)) & (df['start_dt'].isin(control_dates)),
                'test', 'control'
            )
            df.loc['test', metric] *= effect

            # Линеаризация метрики
            CNTRL_ratio = df.loc['control', metric].sum() / df.loc['control', unit].sum()
            df['linearized_metric'] = df[metric] - df[unit] * CNTRL_ratio
            CNTRL_ratio_pre = df.loc['control', metric_pre].sum() / df.loc['control', unit_pre].sum()
            df['linearized_metric_pre'] = df[metric_pre] - df[unit_pre] * CNTRL_ratio_pre

            # CUMPED + t-test
            control = df.loc['control']
            test = df.loc['test']   

            control_cumped = cumped(control['linearized_metric'], control[['linearized_metric_pre'] + additional_covariats])
            test_cumped = cumped(test['linearized_metric'], test[['linearized_metric_pre'] + additional_covariats])

            new_list.append(ttest_ind(test_cumped, control_cumped, alternative=alternative).pvalue)       

        # Анализ результатов
        p_val_frame = pd.DataFrame(new_list, columns=['p_val'])
        if effect == 1:
            legend_list.append('A/A')
            p_vals = [str(round(100 * (np.sum(p_val_frame.p_val < alpha).item() / p_val_frame.shape[0]), 2)) + '%' for alpha in alphas]
            print('Ошибки 1 рода:', ', '.join(p_vals[:alphas.index(0.05) + 1]), '|||', ', '.join(p_vals[alphas.index(0.05) + 1:]))
        else:
            legend_list.append(f'lift {round(100*(effect-1.0),2)}%')
            p_vals = [str(round(100*((1 - np.sum(p_val_frame.p_val >= alpha) / p_val_frame.shape[0])), 2)) + '%' for alpha in alphas]
            print(f'{round(100 * (effect - 1), 2)}% uplift:', ', '.join(p_vals[:alphas.index(0.05) + 1]), '|||', ', '.join(p_vals[alphas.index(0.05) + 1:]))
        global_list.append(new_list)  
    plot_pvalue_distribution(global_list, legend_list, [0.05])
    return global_list, legend_list

    
