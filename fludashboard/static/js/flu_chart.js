/* -*- Mode: JavaScript; tab-width: 8; indent-tabs-mode: nil;
   c-basic-offset: 2 -*- */
/* vim: set ts=8 sts=2 et sw=2 tw=80: */
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * SRAGIncidenceChart is used to show Incidence Flu Chart.
  */
class SRAGIncidenceChart{
  /**
   * @param {string} bindTo - DOM ID of the chart container (e.g. "#container").
   * @param {dict} lastWeekYears- Dictionary with the last week of each
      available year (e.g. {2015: 53, 2016: 52}).
   */
  constructor(bindTo, lastWeekYears) {
    this.bindTo = bindTo;
    this.lastWeekYears = lastWeekYears;
  }

  /**
   * Shows activity information about the criteria established on the chart.
   * @param {string} dataset - dataset
   * @param {string} scale - data scale
   * @param {number} year - SRAG incidence year (e.g. 2013).
   * @param {number} week - SRAG incidence week (e.g. 2).
   * @param {string} territoryName - Federal state name (e.g. "Acre").
   */
  displayInfo(dataset, scale, year, week, territoryName) {
    var url = [
        '.', 'data', dataset, scale, year, week, territoryName, 'levels'
    ].join('/');

    $.getJSON({
      url: url,
      success: function(d) {
        // hidden  all
        var _prob = $('#chart-incidence-activity-level-panel .prob');
        var _level = $('#chart-incidence-activity-level-panel .level');

        if (!_prob.hasClass('hidden')) {
          _prob.addClass('hidden');
        }

        if (!_level.hasClass('hidden')) {
          _level.addClass('hidden');
        }

        // if no data returned
        if (d.length <1) {
          return;
        }

        var data = d[0];

        if (data['situation'] == 'stable') {
          $('.classification', _level).text(
            data['l0'] == 100 ?
              'Baixa' : data['l1'] == 100 ?
              'Epidêmica' : data['l2'] == 100 ?
              'Alta' : data['l3'] == 100 ?
              'Muito Alta' : '(Não encontrada.)'
          );
          _level.removeClass('hidden');
        } else {
          $('.low', _prob).text(data['l0']);
          $('.epidemic', _prob).text(data['l1']);
          $('.high', _prob).text(data['l2']);
          $('.very-high', _prob).text(data['l3']);
          _prob.removeClass('hidden');
        }
      }
    });
  }

  /**
   * Plots SRAG incidence chart
   * @param {string} dataset - dataset
   * @param {string} scale - data scale
   * @param {number} year - SRAG incidence year (e.g. 2013).
   * @param {number} week - SRAG incidence week (e.g. 2).
   * @param {string} territoryName- Federal state name (e.g. "Acre").
   * @return {object} - Chart object.
   */
  plot(dataset, scale, year, week, territoryName) {
    var _this = this;
    var y_label = '';
    var url = [
        '.', 'data', dataset, scale, year, week,
        territoryName, 'weekly-incidence-curve'
    ].join('/');

    $(this.bindTo).empty();

    if (scale == 'incidence') {
        $('#chart-incidence-case-title').text('Curva de Incidência');
        y_label = 'Incidência (por 100 mil habitantes)';
    } else {
        $('#chart-incidence-case-title').text('Série temporal');
        y_label = 'Número de casos';
    }

    var chart = c3.generate({
      bindto: _this.bindTo,
      data: {
        url: url,
        x: 'epiweek',
        names: {
          typical_low: 'Zona de Êxito',
          typical_median: 'Zona de Segurança',
          typical_high: 'Zona de Alerta',
          typical_very_high: 'Zona de Surto',
          value: 'Casos notificados',
          pre_epidemic_threshold: 'Limiar Pré epidêmico',
          high_threshold: 'Intensidade Alta',
          very_high_threshold: 'Intensidade Muito Alta',
          estimated_cases: 'Casos estimados',
          ci_lower: 'Intervalo de confiança inferior',
          ci_upper: 'Intervalo de confiança superior',
          incomplete_data: 'Dados Incompletos'
        },
        types: {
          typical_low: 'area',
          typical_median: 'area',
          typical_high: 'area',
          typical_very_high: 'area',
          value: 'line',
          pre_epidemic_threshold: 'line',
          high_threshold: 'line',
          very_high_threshold: 'line'
        },
        colors: {
          typical_low: '#00ff00',
          typical_median: '#ffff00',
          typical_high: '#ff9900',
          typical_very_high: '#ff0000',
          value: '#000000',
          pre_epidemic_threshold: '#00ff00',
          high_threshold: '#0000ff',
          very_high_threshold: '#ff0000',
          estimated_cases: '#ff0000',
          ci_lower: '#000000',
          ci_upper: '#000000',
          incomplete_data: '#ff0000',
        }
      },
      axis: {
        x: {
          label: {
            text: 'SE',
            position: 'outer-center'
          },
          tick: {
            values: d3.range(1, _this.lastWeekYears[year], 2)
          },
          min: 1,
          max:_this.lastWeekYears[year],
          padding: {
            left: 0,
            right: 0,
          }
        },
        y: {
          label: {
            text: y_label,
            position: 'outer-middle'
          }
        },
      },
      /*regions: [
        {start: 1, end: _this.lastWeekYears[year], class: 'alert-red'}
      ],*/
      grid: {
        x: {
         lines: [
          {value: week, text: 'Semana Selecionada', position: 'middle'}
        ], show: false
        },
        y: {show: true}
      },
      zoom: {
        enabled: true
      },/*
      subchart: {
        show: true
      },*/
      tooltip: {
        show: false
      },
      point: {
        show: false
      },
      legend: {
        position: 'right'
      }
    });

    this.displayInfo(dataset, scale, year, week, territoryName);

    return chart;
  }
}

/**
 * SRAG Incidence Chart by Age
 * @class
 */
class SRAGAgeChart{
  /**
   * @param {string} bindTo - DOM ID of the chart container (e.g. "#container").
   */
  constructor(bindTo) {
    this.bindTo = bindTo;
  }

  /**
   * Plots SRAG incidence chart by age
   * @param {string} dataset - dataset
   * @param {string} scale - data scale
   * @param {number} year - SRAG incidence year.
   * @param {number} week - SRAG incidence week.
   * @param {string} territoryName- Federal state name (e.g. "Acre").
   */
  plot(dataset, scale, year, week, territoryName) {
    var _this = this;
    var y_label;
    var url = [
        '.', 'data', dataset, scale, year, week,
        territoryName, 'age-distribution'
    ].join('/');

    $(this.bindTo).empty();

    if (scale == 'incidence') {
        y_label = 'Incidência (por 100 mil habitantes)';
    } else {
        y_label = 'Número de casos';
    }

    return c3.generate({
      bindto: _this.bindTo,
      data: {
        url: url,
        x: 'index',
        type: 'bar'
      },
      axis: {
        x: {
          label: {
            text: 'Faixa Etária',
            position: 'outer-center'
          },
          type: 'category',

        },
        y: {
          label: {
            text: y_label,
            position: 'outer-middle'
          }
        },
      },
      grid: {
        x: { show: false },
        y: {show: true }
      },
    });
  }
}