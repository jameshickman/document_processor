import {BaseComponent} from '../lib/component_base.js';
import { HTTP_GET, HTTP_POST_JSON, HTTP_DELETE, HTTP_POST_FORM } from "../lib/API.js";
import {multicall} from '../lib/jsum.js';
import {html, css} from "lit";

export class UsageReportingDashboard extends BaseComponent {
    static properties = {
        loading: {type: Boolean, state: true},
        reportType: {type: String, state: true},
        startDate: {type: String, state: true},
        endDate: {type: String, state: true},
        accountId: {type: Number, state: true},
        accounts: {type: Array, state: true},
        reportData: {type: Object, state: true},
        chartData: {type: Object, state: true},
        selectedTimeRange: {type: String, state: true},
        usageSummary: {type: Array, state: true},
        modelUsage: {type: Array, state: true},
        storageUsage: {type: Array, state: true},
        eventLogs: {type: Array, state: true}
    };

    static styles = css`
        .container {
            display: flex;
            flex-direction: column;
            padding: 20px;
            font-family: Arial, sans-serif;
            height: 100%;
            overflow-y: auto;
        }

        .controls-panel {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 5px;
            margin-bottom: 20px;
            border: 1px solid #dee2e6;
        }

        .control-group {
            display: flex;
            flex-direction: column;
            min-width: 150px;
        }

        .control-group label {
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 5px;
            color: #495057;
        }

        .control-group input,
        .control-group select {
            padding: 8px;
            border: 1px solid #ced4da;
            border-radius: 3px;
            font-size: 14px;
        }

        .buttons-group {
            display: flex;
            gap: 10px;
            align-self: flex-end;
            margin-top: auto;
        }

        .btn {
            padding: 8px 15px;
            border: 1px solid #ccc;
            background: #fff;
            cursor: pointer;
            border-radius: 3px;
            font-size: 14px;
        }

        .btn:hover {
            background: #f0f0f0;
        }

        .btn-primary {
            background: #007bff;
            color: white;
            border-color: #007bff;
        }

        .btn-primary:hover {
            background: #0056b3;
        }

        .btn-success {
            background: #28a745;
            color: white;
            border-color: #28a745;
        }

        .btn-success:hover {
            background: #218838;
        }

        .reports-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .report-card {
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .report-card h3 {
            margin-top: 0;
            margin-bottom: 15px;
            color: #495057;
            border-bottom: 1px solid #eee;
            padding-bottom: 8px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }

        .stat-item {
            text-align: center;
            padding: 10px;
        }

        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }

        .stat-label {
            font-size: 12px;
            color: #6c757d;
        }

        .chart-container {
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
            height: 300px;
        }

        .chart-placeholder {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #6c757d;
            font-style: italic;
        }

        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }

        .data-table th,
        .data-table td {
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }

        .data-table th {
            background-color: #f8f9fa;
            font-weight: bold;
            color: #495057;
        }

        .data-table tr:hover {
            background-color: #f8f9fa;
        }

        .loading {
            text-align: center;
            padding: 20px;
            color: #6c757d;
        }

        .tabs {
            display: flex;
            margin-bottom: 15px;
            border-bottom: 1px solid #dee2e6;
        }

        .tab {
            padding: 10px 20px;
            cursor: pointer;
            background: #e9ecef;
            border: 1px solid #dee2e6;
            border-bottom: none;
            border-radius: 5px 5px 0 0;
            margin-right: 5px;
        }

        .tab.active {
            background: white;
            border-bottom: 1px solid white;
            margin-bottom: -1px;
            font-weight: bold;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        .time-range-selector {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .export-section {
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 5px;
            border: 1px solid #dee2e6;
        }

        .export-controls {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
    `;

    constructor() {
        super();
        this.loading = false;
        this.reportType = 'summary';
        this.startDate = this.getDefaultStartDate();
        this.endDate = this.getDefaultEndDate();
        this.accountId = null;
        this.accounts = [];
        this.reportData = null;
        this.chartData = null;
        this.selectedTimeRange = 'custom';
        this.usageSummary = [];
        this.modelUsage = [];
        this.storageUsage = [];
        this.eventLogs = [];
        this.chart = null; // Store chart instance
    }

    getDefaultStartDate() {
        const date = new Date();
        date.setDate(date.getDate() - 30);
        return date.toISOString().split('T')[0];
    }

    getDefaultEndDate() {
        const date = new Date();
        return date.toISOString().split('T')[0];
    }

    server_interface(api) {
        this.init_server(api);

        // Define endpoints for reporting data
        this.server.define_endpoint(
            "/reporting/usage/summary",
            (resp) => {
                this.usageSummary = resp.data;
                this.loading = false;
                this.requestUpdate();
            },
            HTTP_POST_JSON
        );

        this.server.define_endpoint(
            "/reporting/usage/by-model",
            (resp) => {
                this.modelUsage = resp.data;
                this.loading = false;
                this.requestUpdate();
            },
            HTTP_POST_JSON
        );

        this.server.define_endpoint(
            "/reporting/storage",
            (resp) => {
                this.storageUsage = resp.data;
                this.loading = false;
                this.requestUpdate();
            },
            HTTP_POST_JSON
        );

        this.server.define_endpoint(
            "/reporting/logs",
            (resp) => {
                this.eventLogs = resp.data;
                this.loading = false;
                this.requestUpdate();
            },
            HTTP_POST_JSON
        );

        this.server.define_endpoint(
            "/reporting/accounts",
            (resp) => {
                this.accounts = resp.accounts;
                this.requestUpdate();
            },
            HTTP_GET
        );
    }

    login_success() {
        this.loadAccounts();
        this.loadReportData();
    }

    loadAccounts() {
        this.server.call("/reporting/accounts", HTTP_GET);
    }

    loadReportData() {
        this.loading = true;
        this.requestUpdate();

        // Build filter data for each endpoint
        const summaryData = {
            start_date: this.startDate,
            end_date: this.endDate,
            group_by: 'day'
        };
        if (this.accountId) {
            summaryData.account_id = this.accountId;
        }

        const modelData = {
            start_date: this.startDate,
            end_date: this.endDate
        };
        if (this.accountId) {
            modelData.account_id = this.accountId;
        }

        const storageData = {
            start_date: this.startDate,
            end_date: this.endDate
        };
        if (this.accountId) {
            storageData.account_id = this.accountId;
        }

        const logsData = {
            start_date: this.startDate + 'T00:00:00',
            end_date: this.endDate + 'T23:59:59',
            limit: 100,
            offset: 0
        };
        if (this.accountId) {
            logsData.account_id = this.accountId;
        }

        // Call endpoints with POST and JSON body
        this.server.call("/reporting/usage/summary", HTTP_POST_JSON, summaryData);
        this.server.call("/reporting/usage/by-model", HTTP_POST_JSON, modelData);
        this.server.call("/reporting/storage", HTTP_POST_JSON, storageData);
        this.server.call("/reporting/logs", HTTP_POST_JSON, logsData);
    }

    handleTimeRangeChange(e) {
        this.selectedTimeRange = e.target.value;
        
        const endDate = new Date();
        let startDate = new Date();
        
        switch(this.selectedTimeRange) {
            case 'last7':
                startDate.setDate(endDate.getDate() - 7);
                break;
            case 'last30':
                startDate.setDate(endDate.getDate() - 30);
                break;
            case 'last90':
                startDate.setDate(endDate.getDate() - 90);
                break;
            case 'month':
                startDate = new Date(endDate.getFullYear(), endDate.getMonth(), 1);
                break;
            case 'year':
                startDate = new Date(endDate.getFullYear(), 0, 1);
                break;
            default:
                // Custom range, keep existing dates
                return;
        }
        
        this.startDate = startDate.toISOString().split('T')[0];
        this.endDate = endDate.toISOString().split('T')[0];
        
        this.loadReportData();
    }

    handleDateChange(e) {
        const { name, value } = e.target;
        this[name] = value;
    }

    handleAccountChange(e) {
        this.accountId = e.target.value ? parseInt(e.target.value) : null;
    }

    handleRunReport() {
        this.loadReportData();
    }

    handleExportCSV() {
        // Build query parameters for CSV export
        const params = new URLSearchParams({
            report_type: this.reportType,
            start_date: this.startDate,
            end_date: this.endDate
        });

        if (this.accountId) {
            params.append('account_id', this.accountId);
        }

        // Use the API's download method to export CSV
        const exportUrl = `/reporting/export/csv?${params.toString()}`;
        this.server.download(
            exportUrl,
            null, // no content, using URL
            `usage_report_${this.startDate}_${this.endDate}.csv`,
            null, // auto-detect MIME type
            (filename) => {
                console.log(`Usage report exported as: ${filename}`);
            },
            (error) => {
                console.error('Export failed:', error);
                alert('Export failed. Please try again.');
            }
        );
    }

    renderControls() {
        return html`
            <div class="controls-panel">
                <div class="control-group">
                    <label for="startDate">Start Date</label>
                    <input 
                        type="date" 
                        id="startDate" 
                        .value="${this.startDate}"
                        @change="${this.handleDateChange}"
                        name="startDate"
                    >
                </div>
                
                <div class="control-group">
                    <label for="endDate">End Date</label>
                    <input 
                        type="date" 
                        id="endDate" 
                        .value="${this.endDate}"
                        @change="${this.handleDateChange}"
                        name="endDate"
                    >
                </div>
                
                <div class="control-group time-range-selector">
                    <label for="timeRange">Quick Range</label>
                    <select id="timeRange" .value="${this.selectedTimeRange}" @change="${this.handleTimeRangeChange}">
                        <option value="custom">Custom</option>
                        <option value="last7">Last 7 Days</option>
                        <option value="last30">Last 30 Days</option>
                        <option value="last90">Last 90 Days</option>
                        <option value="month">This Month</option>
                        <option value="year">This Year</option>
                    </select>
                </div>
                
                <div class="control-group">
                    <label for="accountId">Account</label>
                    <select id="accountId" @change="${this.handleAccountChange}" .value="${this.accountId || ''}">
                        <option value="">All Accounts</option>
                        ${this.accounts.map(account => html`
                            <option value="${account.id}">${account.name}</option>
                        `)}
                    </select>
                </div>
                
                <div class="buttons-group">
                    <button class="btn btn-primary" @click="${this.handleRunReport}" ?disabled="${this.loading}">
                        ${this.loading ? 'Loading...' : 'Run Report'}
                    </button>
                    <button class="btn" @click="${this.loadReportData}" ?disabled="${this.loading}" title="Refresh current report">
                        ↻ Refresh
                    </button>
                    <button class="btn btn-success" @click="${this.handleExportCSV}" ?disabled="${this.loading}">
                        Export CSV
                    </button>
                </div>
            </div>
        `;
    }

    renderSummaryStats() {
        // Calculate summary statistics from usage data
        let totalOperations = 0;
        let totalTokens = 0;
        let workbenchOps = 0;
        let apiOps = 0;
        let successfulOps = 0;
        let failedOps = 0;

        this.usageSummary.forEach(item => {
            totalOperations += item.total_operations || 0;
            totalTokens += item.total_tokens || 0;
            workbenchOps += item.workbench_operations || 0;
            apiOps += item.api_operations || 0;
            successfulOps += item.successful_operations || 0;
            failedOps += item.failed_operations || 0;
        });

        return html`
            <div class="reports-container">
                <div class="report-card">
                    <h3>Overall Usage</h3>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <div class="stat-value">${totalOperations.toLocaleString()}</div>
                            <div class="stat-label">Total Operations</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${totalTokens.toLocaleString()}</div>
                            <div class="stat-label">Total Tokens</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${workbenchOps.toLocaleString()}</div>
                            <div class="stat-label">Workbench Ops</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${apiOps.toLocaleString()}</div>
                            <div class="stat-label">API Ops</div>
                        </div>
                    </div>
                </div>
                
                <div class="report-card">
                    <h3>Success Rates</h3>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <div class="stat-value">${successfulOps.toLocaleString()}</div>
                            <div class="stat-label">Successful</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${failedOps.toLocaleString()}</div>
                            <div class="stat-label">Failed</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${totalOperations > 0 ? ((successfulOps / totalOperations) * 100).toFixed(1) : 0}%</div>
                            <div class="stat-label">Success Rate</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${totalOperations > 0 ? ((failedOps / totalOperations) * 100).toFixed(1) : 0}%</div>
                            <div class="stat-label">Failure Rate</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    updated(changedProperties) {
        super.updated(changedProperties);

        // Update chart when usage summary data changes
        if (changedProperties.has('usageSummary') && this.usageSummary.length > 0) {
            this.updateChart();
        }
    }

    updateChart() {
        const canvas = this.shadowRoot.querySelector('#usageChart');
        if (!canvas || !window.Chart) {
            return;
        }

        // Prepare data for chart
        const sortedData = [...this.usageSummary].sort((a, b) => new Date(a.date) - new Date(b.date));
        const labels = sortedData.map(item => item.date);
        const totalOps = sortedData.map(item => item.total_operations || 0);
        const workbenchOps = sortedData.map(item => item.workbench_operations || 0);
        const apiOps = sortedData.map(item => item.api_operations || 0);
        const tokens = sortedData.map(item => (item.total_tokens || 0) / 1000); // Convert to thousands

        // Destroy existing chart if it exists
        if (this.chart) {
            this.chart.destroy();
        }

        // Create new chart
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Total Operations',
                        data: totalOps,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        tension: 0.1,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Workbench',
                        data: workbenchOps,
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        tension: 0.1,
                        yAxisID: 'y'
                    },
                    {
                        label: 'API',
                        data: apiOps,
                        borderColor: 'rgb(255, 159, 64)',
                        backgroundColor: 'rgba(255, 159, 64, 0.1)',
                        tension: 0.1,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Tokens (K)',
                        data: tokens,
                        borderColor: 'rgb(153, 102, 255)',
                        backgroundColor: 'rgba(153, 102, 255, 0.1)',
                        tension: 0.1,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Daily Usage Trends'
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Operations'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Tokens (thousands)'
                        },
                        grid: {
                            drawOnChartArea: false,
                        }
                    }
                }
            }
        });
    }

    renderUsageChart() {
        return html`
            <div class="chart-container">
                <canvas id="usageChart"></canvas>
            </div>
        `;
    }

    renderDetailedTables() {
        return html`
            <div class="tabs">
                <div class="tab ${this.reportType === 'summary' ? 'active' : ''}" @click="${() => this.reportType = 'summary'}">Usage Summary</div>
                <div class="tab ${this.reportType === 'model' ? 'active' : ''}" @click="${() => this.reportType = 'model'}">Model Usage</div>
                <div class="tab ${this.reportType === 'storage' ? 'active' : ''}" @click="${() => this.reportType = 'storage'}">Storage</div>
                <div class="tab ${this.reportType === 'logs' ? 'active' : ''}" @click="${() => this.reportType = 'logs'}">Event Logs</div>
            </div>
            
            <div class="tab-content ${this.reportType === 'summary' ? 'active' : ''}">
                <h3>Usage Summary</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Account</th>
                            <th>Total Ops</th>
                            <th>Workbench</th>
                            <th>API</th>
                            <th>Tokens</th>
                            <th>Success</th>
                            <th>Fail</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.usageSummary.slice(0, 10).map(item => html`
                            <tr>
                                <td>${item.date}</td>
                                <td>${item.account_name}</td>
                                <td>${item.total_operations.toLocaleString()}</td>
                                <td>${item.workbench_operations.toLocaleString()}</td>
                                <td>${item.api_operations.toLocaleString()}</td>
                                <td>${item.total_tokens.toLocaleString()}</td>
                                <td>${item.successful_operations.toLocaleString()}</td>
                                <td>${item.failed_operations.toLocaleString()}</td>
                            </tr>
                        `)}
                    </tbody>
                </table>
            </div>
            
            <div class="tab-content ${this.reportType === 'model' ? 'active' : ''}">
                <h3>Model Usage</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Account</th>
                            <th>Provider</th>
                            <th>Model</th>
                            <th>Ops</th>
                            <th>Input Tokens</th>
                            <th>Output Tokens</th>
                            <th>Success</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.modelUsage.slice(0, 10).map(item => html`
                            <tr>
                                <td>${item.date}</td>
                                <td>${item.account_name}</td>
                                <td>${item.provider}</td>
                                <td>${item.model_name}</td>
                                <td>${item.operation_count.toLocaleString()}</td>
                                <td>${item.input_tokens.toLocaleString()}</td>
                                <td>${item.output_tokens.toLocaleString()}</td>
                                <td>${item.successful_operations.toLocaleString()}</td>
                            </tr>
                        `)}
                    </tbody>
                </table>
            </div>
            
            <div class="tab-content ${this.reportType === 'storage' ? 'active' : ''}">
                <h3>Storage Usage</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Account</th>
                            <th>Total GB</th>
                            <th>Docs</th>
                            <th>PDF</th>
                            <th>DOCX</th>
                            <th>Other</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.storageUsage.slice(0, 10).map(item => html`
                            <tr>
                                <td>${item.date}</td>
                                <td>${item.account_name}</td>
                                <td>${item.total_gb.toFixed(2)}</td>
                                <td>${item.document_count.toLocaleString()}</td>
                                <td>${(item.pdf_bytes / (1024**3)).toFixed(2)}</td>
                                <td>${(item.docx_bytes / (1024**3)).toFixed(2)}</td>
                                <td>${(item.other_bytes / (1024**3)).toFixed(2)}</td>
                            </tr>
                        `)}
                    </tbody>
                </table>
            </div>
            
            <div class="tab-content ${this.reportType === 'logs' ? 'active' : ''}">
                <h3>Event Logs</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Account</th>
                            <th>Type</th>
                            <th>Source</th>
                            <th>Status</th>
                            <th>Tokens</th>
                            <th>Duration</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.eventLogs.slice(0, 10).map(item => html`
                            <tr>
                                <td>${item.timestamp.substring(0, 19)}</td>
                                <td>${item.account_name}</td>
                                <td>${item.operation_type}</td>
                                <td>${item.source_type}</td>
                                <td>${item.status}</td>
                                <td>${item.total_tokens ? item.total_tokens.toLocaleString() : '-'}</td>
                                <td>${item.duration_ms ? `${item.duration_ms}ms` : '-'}</td>
                            </tr>
                        `)}
                    </tbody>
                </table>
            </div>
        `;
    }

    render() {
        return html`
            <div class="container">
                <h2>Usage Reporting Dashboard</h2>
                
                ${this.renderControls()}
                
                ${this.loading 
                    ? html`<div class="loading">Loading usage data...</div>` 
                    : html`
                        ${this.renderSummaryStats()}
                        ${this.renderUsageChart()}
                        ${this.renderDetailedTables()}
                        
                        <div class="export-section">
                            <h3>Export Data</h3>
                            <div class="export-controls">
                                <button class="btn btn-success" @click="${this.handleExportCSV}">
                                    Export All Data as CSV
                                </button>
                                <small>Select a date range and account above to filter the exported data</small>
                            </div>
                        </div>
                    `
                }
            </div>
        `;
    }
}

customElements.define('usage-reporting-dashboard', UsageReportingDashboard);