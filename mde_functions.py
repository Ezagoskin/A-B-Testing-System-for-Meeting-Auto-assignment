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

def switchback_linearized_cuped_long(result, result_pre, metric, unit, days, effects, alphas=[0.01, 0.0125, 0.0167, 0.025, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5], alternative='greater', n_runs=500, full_population=True):
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
    for effect in sorted(effects):
        new_list = []
        for d in pd.date_range(start_dt, pd.Timestamp(end_dt) - pd.Timedelta(days=days - 1)):
            res = result[(result['start_dt'] >= d) & (result['start_dt'] <= d + pd.Timedelta(days=days - 1))]
            
            # Добавить данные, полученные до эксперимента
            res = res.merge(result_pre[result_pre['exp_start_dt'] == d], on=['region_id', 'weekday'], how='left')
            # Заменить пропуски в unit_pre на среднее значение для данного региона
            res.loc[res[res['exp_start_dt'].isna()].index, unit_pre] = np.array(res[res['exp_start_dt'].isna()].merge(res[res['region_id'].isin(res[res['exp_start_dt'].isna()]['region_id'].unique())].groupby('region_id', as_index=False).agg({unit: 'mean'}), on='region_id', suffixes=['', '_avg'])[unit + '_avg'])
            # Заменить пропуски в metric_pre на unit_pre * sum(metric_pre) / sum(unit_pre)
            res.loc[res[res['exp_start_dt'].isna()].index, metric_pre] = res[res['exp_start_dt'].isna()][unit_pre] * (res[metric_pre].sum() / res[unit_pre].sum())
            
            for i in range(n_runs):
                
                # Уникальные регионы для теста
                reg_4_test = np.random.choice(unq, int(len(unq) / 2), replace=False)
                if full_population:
                    reg_4_test = unq

                # Оставим встречи в тестовых регионах
                df = res[res['region_id'].isin(reg_4_test)]

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



def switchback_linearized_long(result, metric, unit, days, effects, alpha = 0.05, alternative='two-sided', n_runs=500):
    legend_list = ['random', f'alpha={alpha * 100}%']
    global_list = []
    unq = result['region_id'].unique()
    
    for effect in effects:
        new_list = []
        for d in pd.date_range(START_DATE, pd.Timestamp(END_DATE) - pd.Timedelta(days=days - 1)):
            res = result[(result['start_dt'] >= d) & (result['start_dt'] <= d + pd.Timedelta(days=days - 1))]
            for i in range(n_runs):
                
                # Уникальные регионы для теста
                reg_4_test = np.random.choice(unq, int(len(unq) / 2), replace=False)

                # Оставим встречи в тестовых регионах
                df = res[res['region_id'].isin(reg_4_test)]

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


tf.auth_by_credentials(username='e.zagoskin', password=passward)
gp = tf.Greenplum()

QUERY = """
select *
from usr_deliv.successful_meetings_56
where start_dt between '2025-09-28'::date - 56 - 28 + 2 and '2025-09-28'
"""
df_full = tf.gp_to_df(QUERY, gp_service='orig')

QUERY = """
select *
from usr_deliv.successful_meetings_pre_56
"""
df_pre = tf.gp_to_df(QUERY, gp_service='orig')

days = 56
df_full['start_dt'] = pd.to_datetime(df_full['start_dt'])
df_pre['exp_start_dt'] = pd.to_datetime(df_pre['exp_start_dt'])
df_full['success'] = df_full['success'].astype(float)
df_full.info()


switchback_linearized_cuped_long(result=df_full,result_pre=df_pre, metric='success', unit='meeting_cnt'
                                                                , days=days, effects=[1] + list(np.arange(1.0024, 1.0048, 0.0002))
                                                                , n_runs=500)