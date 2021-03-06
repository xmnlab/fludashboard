from flask import render_template, Flask
# local
from .flu_data import FluDB
from .utils import cross_domain, calc_last_epiweek
from .calc_flu_alert import (
    apply_filter_alert_by_epiweek,
    calc_alert_rank_whole_year)

import pandas as pd


app = Flask(
    __name__,
    template_folder='../templates',
    static_folder='../static'
)

fluDB = FluDB()


def compose_data_url(variables: str):
    """

    :param variables:
    :return:
    """
    url_var = {
        'data': '/data/<int:dataset_id>/<int:scale_id>',
        'year': '<int:year>',
        'epiweek': '<int:epiweek>',
        'territory_type': '<string:territory_type>',
        'territory_id': '<int:territory_id>',
        'territory_name': '<string:territory_name>'
    }

    url = [
        url_var[v] if v in url_var else v
        for v in ['data'] + variables.split('/')
    ]

    return '/'.join(url)


@app.route("/super-header")
def super_header():
    return render_template("super-header.html")


@app.route("/")
def index():
    """

    :return:
    """
    # read data to get the list of available years
    df = fluDB.read_data(
        table_name='historical_estimated_values',
        dataset_id=1, scale_id=1, territory_id=0
    )

    # Here the code should receive the user-requested year.
    # By default should be the current or latest available
    list_of_years = list(set(df.epiyear))

    epiyear = df.base_epiyear.max()
    epiweek = df.base_epiweek.max()

    last_week_years = {
        y: calc_last_epiweek(y) for y in list_of_years
    }

    return render_template(
        "index.html",
        current_epiweek=epiweek,
        list_of_years=sorted(list_of_years, reverse=True),
        last_year=epiyear,
        last_week_years=last_week_years
    )


@app.route("/help")
def app_help():
    """

    :return:
    """
    return render_template("help.html")


@app.route(compose_data_url('year/territory_type'))
def get_data(
    dataset_id: int, scale_id: str, year: int, territory_type: str
):
    """

    :param dataset_id:
    :param scale_id:
    :param year:
    :param territory_type:
    :return:
    """
    territory_type_id = 1 if territory_type == 'state' else 2

    df = fluDB.get_data(
        dataset_id=dataset_id, scale_id=scale_id, year=year,
        territory_type_id=territory_type_id, show_historical_weeks=False
    )
    return apply_filter_alert_by_epiweek(df).to_json(orient='records')


@app.route(compose_data_url('year/epiweek/weekly-incidence-curve'))
@app.route(compose_data_url(
    'year/epiweek/territory_name/weekly-incidence-curve')
)
def data__weekly_incidence_curve(
    dataset_id: int, scale_id: int, year: int, epiweek: int,
    territory_name: str='Brasil'
):
    """

    :param dataset_id:
    :param scale_id:
    :param year:
    :param territory_name:
    :return:
    """
    if not year > 0:
        return '[]'

    ks = [
        'epiweek', 'typical_low', 'typical_median', 'typical_high',
        'value', 'pre_epidemic_threshold', 'high_threshold',
        'very_high_threshold'
    ]

    territory_id = fluDB.get_territory_id_from_name(territory_name)

    df = fluDB.get_data(
        dataset_id=dataset_id, scale_id=scale_id, year=year, week=epiweek,
        show_historical_weeks=True, territory_id=territory_id
    )

    try:
        ks += ['estimated_cases', 'ci_lower', 'ci_upper']

        k = 'estimated_cases'
        ks.pop(ks.index(k))
        ks.insert(ks.index('value') + 1, k)
    except:
        pass

    try:
        min_week = int(df.loc[df['situation_id'] == 0, 'epiweek'].min())
        mask = df['epiweek'] >= min_week

        df['incomplete_data'] = None
        df.loc[mask, 'incomplete_data'] = df.loc[mask, 'ci_upper']

        ks += ['incomplete_data']
    except:
        pass

    # cheating: using a new field corredor_muito_alto just for plotting
    df['typical_very_high'] = df.very_high_threshold.max() * 1.02
    # change keys' order
    ks.insert(ks.index('typical_high') + 1, 'typical_very_high')

    return df[ks].to_csv(index=False, na_rep='null')


@app.route(compose_data_url('year/levels'))
@app.route(compose_data_url('year/epiweek/levels'))
@app.route(compose_data_url('year/epiweek/territory_name/levels'))
def data__incidence_levels(
    dataset_id: int, scale_id: int, year: int,
    epiweek: int=None, territory_name: str='Brasil'
):
    """
    When epiweek==None, the system will assume the whole year view.
    When state_name==None, the system will assume state_name=='Brasil'

    :param dataset_id:
    :param scale_id:
    :param year:
    :param epiweek:
    :param territory_name:
    :return:
    """
    if not year > 0:
        return '[]'

    territory_id = fluDB.get_territory_id_from_name(territory_name)

    df = fluDB.get_data(
        dataset_id=dataset_id, scale_id=scale_id, year=year,
        territory_id=territory_id, week=epiweek
    )

    if epiweek is not None and epiweek > 0:
        ks = [
            'low_level', 'epidemic_level',
            'high_level', 'very_high_level'
        ]
        df[ks] *= 100
        df[ks] = df[ks].round(2)

        ks += ['situation_id']
        return df[ks].to_json(orient='records')

    # prepare data for the whole year
    df = apply_filter_alert_by_epiweek(df=df)

    se = pd.Series({
        'low_level': df[df.alert == 1].count().low_level,
        'epidemic_level': df[df.alert == 2].count().epidemic_level,
        'high_level': df[df.alert == 3].count().high_level,
        'very_high_level': df[df.alert == 4].count().very_high_level
    })

    rank = calc_alert_rank_whole_year(se)

    se.l0 = 0
    se.l1 = 0
    se.l2 = 0
    se.l3 = 0
    se['l%s' % (rank-1)] = 1
    se['situation'] = ''

    return (pd.DataFrame(se).T*100).round(2).to_json(orient='records')


@app.route(compose_data_url('year/data-table'))
@app.route(compose_data_url('year/epiweek/data-table'))
@app.route(compose_data_url('year/epiweek/territory_type/data-table'))
@app.route(
    compose_data_url(
        'year/epiweek/territory_type' +
        '/territory_name/data-table'
    )
)
def data__data_table(
    dataset_id: str, scale_id: str, year: int, epiweek: int=None,
    territory_type: str=None, territory_name: str=None
):
    """
    1. Total number of cases in the selected year for eac
       State + same data for the Country
    2. Number of cases in the selected week for each
       State + same data for the Country
    3. Total number of cases in the selected year for selected State
    4. Number of cases in the selected week for selected State.

    :param dataset_id:
    :param scale_id:
    :param year:
    :param epiweek:
    :param territory_type:
    :param territory_name:
    :return:

    """
    if not year > 0:
        return '{"data": []}'

    ks = [
        'territory_name',
        'epiweek',
        'situation_name',
        'value'
    ]

    if territory_name is not None:
        territory_id = fluDB.get_territory_id_from_name(territory_name)
    else:
        territory_id = None

    df = fluDB.get_data(
        dataset_id=dataset_id, scale_id=scale_id, year=year, week=epiweek,
        territory_id=territory_id
    )

    if territory_type == 'state':
        mask = ~(df.territory_type_name == 'Regional')
    else:
        mask = ~(df.territory_type_name == 'Estado')

    df = df[mask]

    # for a whole year view
    if not epiweek:
        df = fluDB.group_data_by_season(df, season=year)

    # order by type
    df = df.assign(type_unit=1)

    try:
        df.loc[df.uf == 'BR', 'type_unit'] = 0
    except:
        pass

    df.sort_values(
        by=['type_unit', 'territory_name', 'epiyear', 'epiweek'],
        inplace=True
    )
    df.reset_index(drop=True, inplace=True)
    df.drop('type_unit', axis=1, inplace=True)

    # add more information into srag field
    if df.shape[0]:
        if epiweek:
            k = ['estimated_cases', 'ci_lower', 'ci_upper', 'situation_id']
            df.value = df[k].apply(
                lambda row: fluDB.report_incidence(
                    row['estimated_cases'],
                    row['situation_id'],
                    row['ci_lower'], row['ci_upper']
                ), axis=1)
        else:
            df.value = df[['value', 'situation_id']].apply(
                lambda row: fluDB.report_incidence(
                    row['value'], row['situation_id']
                ), axis=1)

        # change situation value by a informative text
        situation_dict = {
            'stable': 'Dado estável. Sujeito a pequenas alterações.',
            'estimated': 'Estimado. Sujeito a alterações.',
            'unknown': 'Dados incompletos. Sujeito a grandes alterações.',
            'incomplete': 'Dados incompletos. Sujeito a grandes alterações.'
        }

        df.situation_name = df.situation_name.map(
            lambda x: situation_dict[x] if x else ''
        )

    return '{"data": %s}' % df[ks].round({
        'value': 2
    }).to_json(orient='records')


@app.route(compose_data_url('year/age-distribution'))
@app.route(compose_data_url('year/epiweek/age-distribution'))
@app.route(compose_data_url('year/epiweek/territory_name/age-distribution'))
@cross_domain(origin='*')
def data__age_distribution(
    dataset_id: str, scale_id: str, year: int,
    epiweek: int=None, territory_name: str=None
):
    """

    :param dataset_id:
    :param scale_id:
    :param year:
    :param epiweek: 0 == all weeks
    :param territory_name:
    :return:
    """
    if not year > 0:
        return '[]'

    if not territory_name:
        territory_name = 'Brasil'

    territory_id = fluDB.get_territory_id_from_name(territory_name)

    df = pd.DataFrame(
        fluDB.get_data_age_sex(
            dataset_id=dataset_id, scale_id=scale_id,
            year=year, week=epiweek, territory_id=territory_id
        )
    ).round(2)

    # TODO: rename the data on the front-end side
    df.rename(index={
        'years_0_4': '0-4 anos',
        'years_5_9': '5-9 anos',
        'years_10_19': '10-19 anos',
        'years_20_29': '20-29 anos',
        'years_30_39': '30-39 anos',
        'years_40_49': '40-49 anos',
        'years_50_59': '50-59 anos',
        'years_60_or_more': '60+ anos'
    }, inplace=True)

    # the replace is used when there is no data in the df
    return ('index' + df.to_csv()).replace('""', '')
