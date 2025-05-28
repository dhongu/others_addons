/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { loadJS } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { formatFloat } from "@web/views/fields/formatters";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component, onWillStart, useEffect, useRef } from "@odoo/owl";

export class FineTuningGraphField extends Component {
    setup() {
        this.chart = null;
        this.canvasRef = useRef("canvas");

        onWillStart(() => loadJS("/web/static/lib/Chart/Chart.js"));

        useEffect(() => {
            this.renderChart();
            return () => {
                if (this.chart) {
                    this.chart.destroy();
                }
            };
        });
    }

    get formattedValue() {
        return formatFloat(this.props.value, { humanReadable: true, decimals: 1 });
    }

    renderChart() {
        const data = this.props.value;
        const config = {
            type: "line",
            data: {
                labels: data['labels'],
                datasets: [
                    {
                        data: data['train_loss'],
                        backgroundColor: "rgba(52,156,227,0.68)",
                        borderColor: "rgba(52,156,227,0.68)",
                        label: 'Train Loss',
                        fill: false,
                        lineTension: 0,
                    },
                    {
                        data: data['valid_loss'],
                        backgroundColor: "rgba(56,189,103,0.62)",
                        borderColor: "rgba(56,189,103,0.62)",
                        label: 'Valid Loss',
                        fill: false,
                        lineTension: 0,
                    },
                    {
                        data: data['valid_mean_token_accuracy'],
                        backgroundColor: "rgba(154,44,197,0.57)",
                        borderColor: "rgba(154,44,197,0.57)",
                        label: 'Valid Mean Token Accuracy',
                        fill: false,
                        lineTension: 0,
                    },
                ],
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                },
                title: {
                    display: true,
                    text: this.props.title,
                    padding: 4,
                },
                scales: {
                    xAxes: [
                        {
                            display: true,
                            scaleLabel: {
                                display: true,
                                labelString: _t("Steps"),
                                fontStyle: 'bold',
                            },
                        }
                    ],
                    yAxes: [
                        {
                            display: true,
                            ticks: {
                                beginAtZero: true,
                            },
                        }
                    ],
                },
                layout: {
                    padding: {
                        bottom: 5,
                    },
                },
            },
        };
        this.chart = new Chart(this.canvasRef.el, config);
    }
}

FineTuningGraphField.template = "web.FineTuningGraphField";
FineTuningGraphField.props = {
    ...standardFieldProps,
    title: { type: String },
};

FineTuningGraphField.extractProps = ({ attrs, field }) => {
    return {
        title: attrs.options.title || field.string,
    };
};

registry.category("fields").add("fine_tuning_graph", FineTuningGraphField);
