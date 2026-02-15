{% extends 'layout.html' %}
{% block content %}
<style>
    @media print {
        .navbar, .btn, .no-print, .form-cobro, .filter-box { display: none !important; }
        .card { border: none !important; box-shadow: none !important; }
        .print-only { display: block !important; }
        body { background: white !important; padding: 0; }
        .table { width: 100% !important; border-collapse: collapse; }
        th, td { border: 1px solid #dee2e6 !important; padding: 8px !important; font-size: 12px; }
    }
    .print-only { display: none; }
</style>

<div class="d-flex justify-content-between align-items-center mb-4 no-print">
    <h4 class="fw-bold mb-0">Facturación</h4>
    <button onclick="window.print();" class="btn btn-dark shadow-sm">
        <i class="fas fa-print me-2"></i>Imprimir Reporte
    </button>
</div>

<div class="print-only text-center mb-4">
    <h2 class="fw-bold">MAURO PILATES</h2>
    <h5>Reporte de Pagos: {{ mes_seleccionado or 'Todos los meses' }}</h5>
    <p class="small text-muted">Generado: {{ datetime.now().strftime('%d/%m/%Y %H:%M') }}</p>
    <hr>
</div>

<div class="row g-4">
    <div class="col-lg-4 form-cobro no-print">
        <div class="card border-0 shadow-sm">
            <div class="card-header bg-primary text-white py-3">
                <h6 class="mb-0 fw-bold">Registrar Cobro</h6>
            </div>
            <div class="card-body">
                <form action="/registrar_pago" method="POST">
                    <div class="mb-3">
                        <label class="form-label small fw-bold">Alumno</label>
                        <select name="alumno_id" class="form-select" required>
                            <option value="">Seleccionar...</option>
                            {% for a in alumnos %}
                            <option value="{{ a.id }}">{{ a.apellido }}, {{ a.nombre }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="row">
                        <div class="col-6 mb-3">
                            <label class="form-label small fw-bold">Concepto</label>
                            <select name="concepto" class="form-select">
                                <option value="Cuota Mensual">Cuota Mensual</option>
                                <option value="Clase Suelta">Clase Suelta</option>
                            </select>
                        </div>
                        <div class="col-6 mb-3">
                            <label class="form-label small fw-bold">Mes</label>
                            <select name="mes" class="form-select">
                                {% for m in ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'] %}
                                <option value="{{ m }}" {% if m == 'Febrero' %}selected{% endif %}>{{ m }}</option>
                                {% endfor %}
                            </select>
                        </div>
                    </div>
                    <div class="mb-4">
                        <label class="form-label small fw-bold">Monto ($)</label>
                        <input type="number" name="monto" class="form-control form-control-lg text-success fw-bold" placeholder="0.00" required>
                    </div>
                    <button type="submit" class="btn btn-success w-100 py-2 fw-bold rounded-pill">REGISTRAR PAGO</button>
                </form>
            </div>
        </div>
    </div>

    <div class="col-lg-8">
        <div class="card border-0 shadow-sm mb-3 no-print filter-box">
            <div class="card-body py-2">
                <form action="/facturacion" method="GET" class="row g-2 align-items-center">
                    <div class="col-auto">
                        <label class="small fw-bold">Ver mes:</label>
                    </div>
                    <div class="col">
                        <select name="mes_filtro" class="form-select form-select-sm" onchange="this.form.submit()">
                            <option value="Todos">Mostrar Todo</option>
                            {% for m in ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'] %}
                            <option value="{{ m }}" {% if m == mes_seleccionado %}selected{% endif %}>{{ m }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-auto">
                        <span class="badge bg-light text-dark">{{ pagos | length }} registros</span>
                    </div>
                </form>
            </div>
        </div>

        <div class="card border-0 shadow-sm">
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover align-middle mb-0">
                        <thead class="table-light">
                            <tr>
                                <th class="px-3">Fecha</th>
                                <th>Alumno</th>
                                <th>Detalle</th>
                                <th class="text-end px-3">Monto</th>
                                <th class="text-center no-print"></th>
                            </tr>
                        </thead>
                        <tbody>
                            {% set total = namespace(valor=0) %}
                            {% for p in pagos %}
                            {% set total.valor = total.valor + p.monto %}
                            <tr>
                                <td class="px-3 small">{{ p.fecha.strftime('%d/%m/%Y') }}</td>
                                <td class="fw-bold text-uppercase">{{ p.alumno_nombre }}</td>
                                <td>{{ p.concepto }}</td>
                                <td class="text-end fw-bold text-success px-3">${{ p.monto }}</td>
                                <td class="text-center no-print">
                                    <a href="/eliminar_pago/{{ p.id }}" class="text-danger" onclick="return confirm('¿Eliminar?')">
                                        <i class="fas fa-trash-alt"></i>
                                    </a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                        <tfoot class="table-dark">
                            <tr>
                                <td colspan="3" class="px-3 fw-bold">TOTAL RECAUDADO</td>
                                <td class="text-end px-3 fw-bold">${{ total.valor }}</td>
                                <td class="no-print"></td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}