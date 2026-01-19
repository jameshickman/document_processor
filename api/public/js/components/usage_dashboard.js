/**
 * Role-aware usage dashboard component
 * - Regular users see their own usage data via /usage/* endpoints
 * - Users with reporting role see all accounts via /reporting/* endpoints
 */

import {BaseComponent} from '../lib/component_base.js';
import { HTTP_GET, HTTP_POST_JSON } from "../lib/API.js";
import {html, css} from "lit";

export class UsageDashboard extends BaseComponent {
    static properties = {
        loading: {type: Boolean, state: true},
        reportType: {type: String, state: true},
        startDate: {type: String, state: true},
        endDate: {type: String, state: true},
        accountId: {type: Number, state: true},
        accounts: {type: Array, state: true},
        selectedTimeRange: {type: String, state: true},
        usageSummary: {type: Array, state: true},
        modelUsage: {type: Array, state: true},
        storageUsage: {type: Array, state: true},
        hasReportingRole: {type: Boolean, state: true},
        userRoles: {type: Array, state: true}
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

        .page-header {
            margin-bottom: 20px;
        }

        .page-header h1 {
            margin: 0 0 10px 0;
            color: #212529;
        }

        .page-header p {
            margin: 0;
            color: #6c757d;
            font-size: 14px;
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

        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            background: white;
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
            padding: 40px;
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
    `;

    constructor() {
        super();
        this.loading = false;
        this.reportType = 'summary';
        this.startDate = this.getDefaultStartDate();
        this.endDate = this.getDefaultEndDate();
        this.accountId = null;
        this.accounts = [];
        this.selectedTimeRange = 'last30';
        this.usageSummary = [];
        this.modelUsage = [];
        this.storageUsage = [];
        this.hasReportingRole = false;
        this.userRoles = [];
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

        // Check user roles from JWT token
        this.checkUserRoles();

        // Define endpoints based on role
        if (this.hasReportingRole) {
            // Administrative endpoints
            this.server.define_endpoint(
                "/reporting/usage/summary",
                (resp) => {
                    this.usageSummary = resp.data || [];
                    this.loading = false;
                    this.requestUpdate();
                },
                HTTP_POST_JSON
            );

            this.server.define_endpoint(
                "/reporting/usage/by-model",
                (resp) => {
                    this.modelUsage = resp.data || [];
                    this.loading = false;
                    this.requestUpdate();
                },
                HTTP_POST_JSON
            );

            this.server.define_endpoint(
                "/reporting/storage",
                (resp) => {
                    this.storageUsage = resp.data || [];
                    this.loading = false;
                    this.requestUpdate();
                },
                HTTP_POST_JSON
            );

            this.server.define_endpoint(
                "/reporting/accounts",
                (resp) => {
                    this.accounts = resp.accounts || [];
                    this.requestUpdate();
                },
                HTTP_GET
            );
        } else {
            // Self-service endpoints
            this.server.define_endpoint(
                "/usage/my-summary",
                (resp) => {
                    this.usageSummary = resp.data || [];
                    this.loading = false;
                    this.requestUpdate();
                },
                HTTP_POST_JSON
            );

            this.server.define_endpoint(
                "/usage/my-models",
                (resp) => {
                    this.modelUsage = resp.data || [];
                    this.loading = false;
                    this.requestUpdate();
                },
                HTTP_POST_JSON
            );

            this.server.define_endpoint(
                "/usage/my-storage",
                (resp) => {
                    this.storageUsage = resp.data || [];
                    this.loading = false;
                    this.requestUpdate();
                },
                HTTP_POST_JSON
            );
        }
    }

    checkUserRoles() {
        // Extract roles from JWT token stored in localStorage
        const token = localStorage.getItem('jwt_token');
        if (token) {
            try {
                // Decode JWT (simple base64 decode of payload)
                const payload = JSON.parse(atob(token.split('.')[1]));
                this.userRoles = payload.roles || [];
                this.hasReportingRole = this.userRoles.includes('reporting') || this.userRoles.includes('admin');
            } catch (e) {
                console.error('Error decoding JWT:', e);
                this.userRoles = [];
                this.hasReportingRole = false;
            }
        }
    }

    login_success() {
        this.checkUserRoles();
        if (this.hasReportingRole) {
            this.loadAccounts();
        }
        this.loadReportData();
    }

    loadAccounts() {
        if (this.hasReportingRole) {
            this.server.call("/reporting/accounts", HTTP_GET);
        }
    }

    loadReportData() {
        this.loading = true;
        this.requestUpdate();

        const baseData = {
            start_date: this.startDate,
            end_date: this.endDate
        };

        if (this.hasReportingRole) {
            // Administrative reporting with optional account filter
            const summaryData = { ...baseData, group_by: 'day' };
            const modelData = { ...baseData };
            const storageData = { ...baseData };

            if (this.accountId) {
                summaryData.account_id = this.accountId;
                modelData.account_id = this.accountId;
                storageData.account_id = this.accountId;
            }

            this.server.call("/reporting/usage/summary", HTTP_POST_JSON, summaryData);
            this.server.call("/reporting/usage/by-model", HTTP_POST_JSON, modelData);
            this.server.call("/reporting/storage", HTTP_POST_JSON, storageData);
        } else {
            // Self-service usage (no account filter)
            const summaryData = { ...baseData, group_by: 'day' };

            this.server.call("/usage/my-summary", HTTP_POST_JSON, summaryData);
            this.server.call("/usage/my-models", HTTP_POST_JSON, baseData);
            this.server.call("/usage/my-storage", HTTP_POST_JSON, baseData);
        }
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
        const exportData = {
            start_date: this.startDate,
            end_date: this.endDate,
            report_type: this.reportType
        };

        if (this.hasReportingRole) {
            if (this.accountId) {
                exportData.account_id = this.accountId;
            }

            // Use POST for export
            this.server.define_endpoint(
                "/reporting/export/csv",
                (resp) => {
                    // Response is already a download
                },
                HTTP_POST_JSON
            );

            // Trigger download via POST
            const exportUrl = '/reporting/export/csv';
            const params = new URLSearchParams(exportData);
            this.server.download(`${exportUrl}?${params.toString()}`);
        } else {
            // Self-service export
            const exportUrl = '/usage/my-export/csv';
            const params = new URLSearchParams(exportData);
            this.server.download(`${exportUrl}?${params.toString()}`);
        }
    }

    render() {
        return html`
            <div class="container">
                <div class="page-header">
                    <h1>${this.hasReportingRole ? 'Usage Reporting' : 'My Usage'}</h1>
                    <p>${this.hasReportingRole ? 'View usage data across all accounts' : 'View your usage data and billing information'}</p>
                </div>

                <div class="controls-panel">
                    <div class="control-group">
                        <label>Time Range</label>
                        <select @change=${this.handleTimeRangeChange} .value=${this.selectedTimeRange}>
                            <option value="last7">Last 7 Days</option>
                            <option value="last30">Last 30 Days</option>
                            <option value="last90">Last 90 Days</option>
                            <option value="month">This Month</option>
                            <option value="year">This Year</option>
                            <option value="custom">Custom Range</option>
                        </select>
                    </div>

                    ${this.selectedTimeRange === 'custom' ? html`
                        <div class="control-group">
                            <label>Start Date</label>
                            <input
                                type="date"
                                name="startDate"
                                .value=${this.startDate}
                                @change=${this.handleDateChange}
                            >
                        </div>

                        <div class="control-group">
                            <label>End Date</label>
                            <input
                                type="date"
                                name="endDate"
                                .value=${this.endDate}
                                @change=${this.handleDateChange}
                            >
                        </div>
                    ` : ''}

                    ${this.hasReportingRole ? html`
                        <div class="control-group">
                            <label>Account</label>
                            <select @change=${this.handleAccountChange}>
                                <option value="">All Accounts</option>
                                ${this.accounts.map(acc => html`
                                    <option value="${acc.id}">${acc.name}</option>
                                `)}
                            </select>
                        </div>
                    ` : ''}

                    <div class="control-group">
                        <label>Report Type</label>
                        <select @change=${(e) => this.reportType = e.target.value} .value=${this.reportType}>
                            <option value="summary">Usage Summary</option>
                            <option value="by_model">By Model</option>
                            <option value="storage">Storage</option>
                        </select>
                    </div>

                    <div class="buttons-group">
                        <button class="btn btn-primary" @click=${this.handleRunReport}>
                            Run Report
                        </button>
                        <button class="btn btn-success" @click=${this.handleExportCSV}>
                            Export CSV
                        </button>
                    </div>
                </div>

                ${this.loading ? html`
                    <div class="loading">Loading usage data...</div>
                ` : this.renderReportData()}
            </div>
        `;
    }

    renderReportData() {
        if (this.reportType === 'summary') {
            return this.renderSummaryData();
        } else if (this.reportType === 'by_model') {
            return this.renderModelData();
        } else if (this.reportType === 'storage') {
            return this.renderStorageData();
        }
        return html``;
    }

    renderSummaryData() {
        if (this.usageSummary.length === 0) {
            return html`<div class="loading">No usage data available for the selected period.</div>`;
        }

        // Calculate totals
        const totals = this.usageSummary.reduce((acc, item) => ({
            total_operations: acc.total_operations + (item.total_operations || 0),
            total_tokens: acc.total_tokens + (item.total_tokens || 0),
            successful_operations: acc.successful_operations + (item.successful_operations || 0),
            failed_operations: acc.failed_operations + (item.failed_operations || 0)
        }), { total_operations: 0, total_tokens: 0, successful_operations: 0, failed_operations: 0 });

        return html`
            <div class="reports-container">
                <div class="report-card">
                    <h3>Overview</h3>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <div class="stat-value">${totals.total_operations.toLocaleString()}</div>
                            <div class="stat-label">Total Operations</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${totals.total_tokens.toLocaleString()}</div>
                            <div class="stat-label">Total Tokens</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${totals.successful_operations.toLocaleString()}</div>
                            <div class="stat-label">Successful</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${totals.failed_operations.toLocaleString()}</div>
                            <div class="stat-label">Failed</div>
                        </div>
                    </div>
                </div>
            </div>

            <table class="data-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        ${this.hasReportingRole ? html`<th>Account</th>` : ''}
                        <th>Total Ops</th>
                        <th>Workbench</th>
                        <th>API</th>
                        <th>Extractions</th>
                        <th>Classifications</th>
                        <th>Tokens</th>
                        <th>Success Rate</th>
                    </tr>
                </thead>
                <tbody>
                    ${this.usageSummary.map(item => html`
                        <tr>
                            <td>${item.date}</td>
                            ${this.hasReportingRole ? html`<td>${item.account_name || 'Unknown'}</td>` : ''}
                            <td>${item.total_operations || 0}</td>
                            <td>${item.workbench_operations || 0}</td>
                            <td>${item.api_operations || 0}</td>
                            <td>${item.extractions || 0}</td>
                            <td>${item.classifications || 0}</td>
                            <td>${(item.total_tokens || 0).toLocaleString()}</td>
                            <td>${item.total_operations > 0 ? ((item.successful_operations / item.total_operations) * 100).toFixed(1) : 0}%</td>
                        </tr>
                    `)}
                </tbody>
            </table>
        `;
    }

    renderModelData() {
        if (this.modelUsage.length === 0) {
            return html`<div class="loading">No model usage data available for the selected period.</div>`;
        }

        return html`
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        ${this.hasReportingRole ? html`<th>Account</th>` : ''}
                        <th>Provider</th>
                        <th>Model</th>
                        <th>Operations</th>
                        <th>Input Tokens</th>
                        <th>Output Tokens</th>
                        <th>Total Tokens</th>
                        <th>Avg Duration</th>
                    </tr>
                </thead>
                <tbody>
                    ${this.modelUsage.map(item => html`
                        <tr>
                            <td>${item.date}</td>
                            ${this.hasReportingRole ? html`<td>${item.account_name || 'Unknown'}</td>` : ''}
                            <td>${item.provider}</td>
                            <td>${item.model_name}</td>
                            <td>${item.operation_count || 0}</td>
                            <td>${(item.input_tokens || 0).toLocaleString()}</td>
                            <td>${(item.output_tokens || 0).toLocaleString()}</td>
                            <td>${(item.total_tokens || 0).toLocaleString()}</td>
                            <td>${item.avg_duration_ms || '-'}ms</td>
                        </tr>
                    `)}
                </tbody>
            </table>
        `;
    }

    renderStorageData() {
        if (this.storageUsage.length === 0) {
            return html`<div class="loading">No storage data available for the selected period.</div>`;
        }

        return html`
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        ${this.hasReportingRole ? html`<th>Account</th>` : ''}
                        <th>Total GB</th>
                        <th>Document Count</th>
                        <th>Storage Backend</th>
                    </tr>
                </thead>
                <tbody>
                    ${this.storageUsage.map(item => html`
                        <tr>
                            <td>${item.date}</td>
                            ${this.hasReportingRole ? html`<td>${item.account_name || 'Unknown'}</td>` : ''}
                            <td>${item.total_gb ? item.total_gb.toFixed(2) : '0.00'}</td>
                            <td>${item.document_count || 0}</td>
                            <td>${item.storage_backend || '-'}</td>
                        </tr>
                    `)}
                </tbody>
            </table>
        `;
    }
}

customElements.define('usage-dashboard', UsageDashboard);
