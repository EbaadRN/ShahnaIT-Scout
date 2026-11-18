# ============ MASTER REPORTING ENGINE: proposals -> JSON / Excel / PDF ============
# Paste this whole block into app.py directly AFTER the dispatch_proposal() route (before "@app.route('/api/candidates/<int:candidate_id>/projects'").
import io
import calendar
from datetime import date as _date, datetime as _datetime, timedelta as _timedelta, timezone as _timezone
from xml.sax.saxutils import escape as _xml_escape

IST = _timezone(_timedelta(hours=5, minutes=30))
REPORT_MAX_ROWS = 5000

REPORT_COLUMNS = [
    'Date of Submission', 'Candidate Name', 'Total Exp', 'Relevant Exp', 'Mobile No', 'Email ID',
    'Requirement (SIT-R-)', 'Client Name', 'HR who proposed', 'CCTC', 'ECTC', 'Location',
    'Onsite/Hybrid/Remote', 'Freelancing (Yes/No)', 'C2C/C2H/FTE', 'Last Working Day', 'Notice Period', 'Remarks',
]

# tracker header text (any spelling the user types) -> canonical column
_REPORT_ALIASES = {
    'dateofsubmission': 'Date of Submission', 'date': 'Date of Submission', 'submissiondate': 'Date of Submission',
    'candidatename': 'Candidate Name', 'name': 'Candidate Name',
    'totalexp': 'Total Exp', 'totalexperience': 'Total Exp', 'totalexpyrs': 'Total Exp',
    'relevantexp': 'Relevant Exp', 'relexp': 'Relevant Exp', 'relevantexperience': 'Relevant Exp',
    'mobileno': 'Mobile No', 'mobile': 'Mobile No', 'phone': 'Mobile No', 'contactno': 'Mobile No',
    'emailid': 'Email ID', 'email': 'Email ID',
    'requirementsitr': 'Requirement (SIT-R-)', 'requirement': 'Requirement (SIT-R-)', 'requirementid': 'Requirement (SIT-R-)',
    'clientname': 'Client Name', 'client': 'Client Name',
    'hrwhoproposed': 'HR who proposed', 'hr': 'HR who proposed', 'hrname': 'HR who proposed',
    'cctc': 'CCTC', 'currentctc': 'CCTC', 'ectc': 'ECTC', 'expectedctc': 'ECTC',
    'location': 'Location',
    'onsitehybridremote': 'Onsite/Hybrid/Remote', 'workmode': 'Onsite/Hybrid/Remote',
    'freelancingyesno': 'Freelancing (Yes/No)', 'freelancing': 'Freelancing (Yes/No)',
    'c2cc2hfte': 'C2C/C2H/FTE', 'engagementtype': 'C2C/C2H/FTE',
    'lastworkingday': 'Last Working Day', 'lwd': 'Last Working Day',
    'noticeperiod': 'Notice Period', 'notice': 'Notice Period',
    'remarks': 'Remarks', 'note': 'Remarks', 'notes': 'Remarks',
}


def _report_key(text):
    return re.sub(r'[^a-z0-9]', '', str(text or '').lower())


def _parse_any_date(text):
    """'01-Nov-2026', '2026-11-01', '01/11/2026', '1 Nov 2026' -> date, or None."""
    s = str(text or '').strip()
    for fmt in ('%d-%b-%Y', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d %b %Y', '%d %B %Y', '%d-%B-%Y', '%d.%m.%Y'):
        try:
            return _datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _dispatch_tracker_rows(raw):
    """Untrusted tracker HTML -> list of {canonical column: text} (first table; first row = headers).
    Columns the user renamed to something unknown are ignored, so the report always has the same 18 columns."""
    parser = _TrackerTableParser()
    try:
        parser.feed(str(raw or '')[:200000])
        parser.close()
    except Exception:
        return []
    rows = [r for r in parser.rows if r]
    if len(rows) < 2:
        return []
    heads = [_REPORT_ALIASES.get(_report_key(c['text'])) for c in rows[0]]
    out = []
    for r in rows[1:51]:
        rec = {}
        for h, cell in zip(heads, r):
            text = '\n'.join(x.strip() for x in cell['text'].split('\n')).strip()[:1000]
            if h and text and h not in rec:
                rec[h] = text
        if rec:
            out.append(rec)
    return out


def _dispatch_record_tracker(log_id, candidate_id, rows):
    """Store the proposal row(s) with the log entry, and remember the new candidate fields for next time. Never raises."""
    if not log_id or not rows:
        return
    try:
        sub = _parse_any_date(rows[0].get('Date of Submission')) or _datetime.now(IST).date()
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute('UPDATE proposal_dispatch_log SET tracker_json = ?, submission_date = ? WHERE id = ?',
                         (json.dumps(rows, ensure_ascii=False), sub.isoformat(), log_id))
            remember = {'relevant_exp': 'Relevant Exp', 'work_mode': 'Onsite/Hybrid/Remote', 'freelancing': 'Freelancing (Yes/No)',
                        'engagement_type': 'C2C/C2H/FTE', 'last_working_day': 'Last Working Day'}
            for col, head in remember.items():
                if rows[0].get(head):
                    conn.execute(f'UPDATE candidates SET {col} = ? WHERE id = ?', (rows[0][head][:200], candidate_id))
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f'dispatch tracker snapshot failed: {e}')


# ---------------------------------------------------------------- query
def _report_range(args):
    """range=day|week|month (+ date=YYYY-MM-DD anchor) or range=custom (+ start, end). Returns (start, end, label)."""
    today = _datetime.now(IST).date()
    kind = (args.get('range') or 'day').strip().lower()
    anchor = _parse_any_date(args.get('date')) or today
    if kind == 'custom':
        start = _parse_any_date(args.get('start')) or anchor
        end = _parse_any_date(args.get('end')) or start
        if end < start:
            start, end = end, start
        if (end - start).days > 366:
            raise ValueError('Custom range cannot be longer than one year')
    elif kind == 'week':
        start = anchor - _timedelta(days=anchor.weekday())
        end = start + _timedelta(days=6)
    elif kind == 'month':
        start = anchor.replace(day=1)
        end = anchor.replace(day=calendar.monthrange(anchor.year, anchor.month)[1])
    elif kind == 'day':
        start = end = anchor
    else:
        raise ValueError('range must be day, week, month or custom')
    label = start.strftime('%d %b %Y') if start == end else f"{start.strftime('%d %b %Y')} to {end.strftime('%d %b %Y')}"
    return start, end, label


def _ordinal_day(d):
    n = d.day
    suffix = 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f'{n:02d}{suffix}'


def _report_day_label(d):
    return f"{_ordinal_day(d)} {d.strftime('%b %Y')} ({d.strftime('%A')})"


def _fallback_row(r):
    """Row built from the candidate record - used for older log entries and for tracker cells left empty."""
    def years(v):
        s = str(v or '').strip()
        return s + ' yrs' if re.fullmatch(r'\d+(\.\d+)?', s) else s
    rel = ', '.join(f"{e['skill']} - {e['years']} yrs" if e.get('years') else e['skill']
                    for e in _dispatch_json_list(r['relevant_experience']) if isinstance(e, dict) and e.get('skill'))
    try:
        notice = f"{int(r['notice_period_days'])} days" if int(r['notice_period_days'] or 0) > 0 else ''
    except (TypeError, ValueError):
        notice = ''
    return {
        'Candidate Name': ' '.join(p for p in [r['first_name'], r['last_name']] if p).strip(),
        'Total Exp': years(r['years_of_experience']),
        'Relevant Exp': (r['relevant_exp'] or rel or ''),
        'Mobile No': r['phone'] or '', 'Email ID': r['email'] or '',
        'Requirement (SIT-R-)': r['proposed_requirement'] or '', 'Client Name': r['proposed_client'] or '',
        'HR who proposed': r['sent_by_name'] or '',
        'CCTC': r['current_ctc'] or '', 'ECTC': r['expected_ctc'] or '', 'Location': r['location'] or '',
        'Onsite/Hybrid/Remote': r['work_mode'] or '', 'Freelancing (Yes/No)': r['freelancing'] or '',
        'C2C/C2H/FTE': r['engagement_type'] or '', 'Last Working Day': r['last_working_day'] or '',
        'Notice Period': notice, 'Remarks': '',
    }


def _report_query(args, user_id, see_all):
    start, end, label = _report_range(args)
    hr_f = (args.get('hr') or '').strip().lower()
    client_f = (args.get('client') or '').strip().lower()
    skills = [s.strip().lower() for s in re.split(r'[,;]', args.get('skill') or '') if s.strip()]
    sql = '''SELECT l.id AS log_id, l.sent_by, l.sent_by_name, l.created_at, l.tracker_json,
                    COALESCE(l.submission_date, date(l.created_at, '+330 minutes')) AS sub_date,
                    c.first_name, c.last_name, c.phone, c.email, c.current_ctc, c.expected_ctc, c.location,
                    c.years_of_experience, c.relevant_experience, c.relevant_exp, c.notice_period_days,
                    c.proposed_client, c.proposed_requirement, c.work_mode, c.freelancing, c.engagement_type,
                    c.last_working_day, c.core_skills, c.designation
             FROM proposal_dispatch_log l LEFT JOIN candidates c ON c.id = l.candidate_id
             WHERE l.status IN ('sent', 'partial')
               AND COALESCE(l.submission_date, date(l.created_at, '+330 minutes')) BETWEEN ? AND ?'''
    params = [start.isoformat(), end.isoformat()]
    if not see_all:
        sql += ' AND l.sent_by = ?'
        params.append(user_id)
    sql += ' ORDER BY sub_date, l.id'
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        found = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    rows = []
    for r in found:
        d = _parse_any_date(r['sub_date']) or start
        base = _fallback_row(r)
        try:
            tracked = json.loads(r['tracker_json']) if r['tracker_json'] else []
        except Exception:
            tracked = []
        for rec in (tracked if isinstance(tracked, list) and tracked else [{}]):
            row = {col: (str(rec.get(col) or '').strip() or str(base.get(col) or '')) for col in REPORT_COLUMNS}
            row['Date of Submission'] = d.strftime('%d-%b-%Y')
            hay = ' '.join(str(x or '') for x in (r['core_skills'], r['relevant_experience'], r['designation'], row['Relevant Exp'])).lower()
            if hr_f and hr_f != row['HR who proposed'].lower():
                continue
            if client_f and client_f not in row['Client Name'].lower():
                continue
            if skills and not any(s in hay for s in skills):
                continue
            row['_date'] = d.isoformat()
            rows.append(row)
            if len(rows) >= REPORT_MAX_ROWS:
                return start, end, label, rows
    return start, end, label, rows


# ---------------------------------------------------------------- Excel (pandas + openpyxl), grouped by date
def _report_xlsx(rows, label):
    import pandas as pd
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    buf = io.BytesIO()
    df = pd.DataFrame(rows, columns=REPORT_COLUMNS + ['_date']) if rows else pd.DataFrame(columns=REPORT_COLUMNS + ['_date'])
    n_cols = len(REPORT_COLUMNS)
    with pd.ExcelWriter(buf, engine='openpyxl') as xw:
        df[REPORT_COLUMNS].head(0).to_excel(xw, sheet_name='Proposals', index=False)        # header row
        ws = xw.sheets['Proposals']
        thin = Side(style='thin', color='B8C2CC')
        box = Border(left=thin, right=thin, top=thin, bottom=thin)
        for col in range(1, n_cols + 1):
            c = ws.cell(row=1, column=col)
            c.font = Font(bold=True, color='FFFFFF')
            c.fill = PatternFill('solid', fgColor='1B2A4A')
            c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            c.border = box
        ws.row_dimensions[1].height = 30
        r = 2
        for d, grp in df.groupby('_date', sort=True):
            ws.cell(row=r, column=1, value=f"{_report_day_label(_date.fromisoformat(d))}  -  {len(grp)} proposal{'s' if len(grp) != 1 else ''}")
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cols)
            band = ws.cell(row=r, column=1)
            band.font = Font(bold=True, color='1B2A4A')
            band.fill = PatternFill('solid', fgColor='E3EAF2')
            band.alignment = Alignment(vertical='center')
            ws.row_dimensions[r].height = 22
            r += 1
            grp[REPORT_COLUMNS].to_excel(xw, sheet_name='Proposals', index=False, header=False, startrow=r - 1)
            for rr in range(r, r + len(grp)):
                for col in range(1, n_cols + 1):
                    c = ws.cell(row=rr, column=col)
                    c.alignment = Alignment(vertical='top', wrap_text=True)
                    c.border = box
            r += len(grp)
        ws.cell(row=r + 1, column=1, value='Proprietary & Confidential - An asset of ShahnaIT').font = Font(italic=True, color='6B7C80', size=9)
        widths = [14, 22, 10, 22, 17, 26, 18, 20, 18, 10, 10, 16, 16, 14, 14, 14, 12, 30]
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = 'A2'
        ws.page_setup.orientation = 'landscape'          # prints on one page width
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.sheet_view.zoomScale = 90
        for row in ws.iter_rows():                                  # text that starts with "=" must never become a formula
            for c in row:
                if isinstance(c.value, str) and c.value.startswith('='):
                    c.data_type = 's'

        summary = pd.DataFrame({'Report': ['Period', 'Total proposals', 'Generated (IST)'],
                                'Value': [label, len(df), _datetime.now(IST).strftime('%d-%b-%Y %H:%M')]})
        summary.to_excel(xw, sheet_name='Summary', index=False)
        if len(df):
            by_date = df.groupby('_date').size().reset_index(name='Proposals').rename(columns={'_date': 'Date'})
            by_hr = df.groupby('HR who proposed').size().reset_index(name='Proposals').sort_values('Proposals', ascending=False)
            by_client = df.groupby('Client Name').size().reset_index(name='Proposals').sort_values('Proposals', ascending=False)
            by_date.to_excel(xw, sheet_name='Summary', index=False, startrow=6)
            by_hr.to_excel(xw, sheet_name='Summary', index=False, startrow=6, startcol=3)
            by_client.to_excel(xw, sheet_name='Summary', index=False, startrow=6, startcol=6)
        sw = xw.sheets['Summary']
        for i, w in enumerate([22, 26, 3, 24, 12, 3, 26, 12], 1):
            sw.column_dimensions[get_column_letter(i)].width = w
        for row in sw.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith('='):
                    c.data_type = 's'
    buf.seek(0)
    return buf


# ---------------------------------------------------------------- PDF (reportlab), grouped by date
def _report_pdf(rows, label):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A3, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    footer = 'Proprietary & Confidential - An asset of ShahnaIT'

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#6B7C80'))
        canvas.drawString(doc.leftMargin, 14, footer)
        canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 14, f'Page {doc.page}')
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=landscape(A3), leftMargin=20, rightMargin=20, topMargin=24, bottomMargin=30,
                            title='Proposal Report', author='ShahnaIT')
    navy = colors.HexColor('#1B2A4A')
    title = ParagraphStyle('t', fontName='Helvetica-Bold', fontSize=16, textColor=navy, leading=20)
    sub = ParagraphStyle('s', fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#44546A'), leading=12)
    head = ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=7, textColor=colors.white, leading=9, alignment=1)
    cell = ParagraphStyle('c', fontName='Helvetica', fontSize=6.8, leading=8.4)
    band = ParagraphStyle('b', fontName='Helvetica-Bold', fontSize=8.5, textColor=navy, leading=11)

    def p(text, style):
        return Paragraph(_xml_escape(str(text or '')).replace('\n', '<br/>'), style)

    n = len(REPORT_COLUMNS)
    weights = [1.0, 1.4, 0.7, 1.4, 1.1, 1.8, 1.2, 1.2, 1.2, 0.7, 0.7, 1.0, 1.2, 0.9, 1.0, 1.0, 0.8, 1.7]
    usable = landscape(A3)[0] - 40
    widths = [usable * w / sum(weights) for w in weights]

    data = [[p(c, head) for c in REPORT_COLUMNS]]
    style = [('BACKGROUND', (0, 0), (-1, 0), navy), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
             ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#B8C2CC')),
             ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
             ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]
    last = None
    for row in rows:
        if row['_date'] != last:
            last = row['_date']
            count = sum(1 for x in rows if x['_date'] == last)
            data.append([p(f"{_report_day_label(_date.fromisoformat(last))}  -  {count} proposal{'s' if count != 1 else ''}", band)] + [''] * (n - 1))
            i = len(data) - 1
            style += [('SPAN', (0, i), (-1, i)), ('BACKGROUND', (0, i), (-1, i), colors.HexColor('#E3EAF2'))]
        data.append([p(row[c], cell) for c in REPORT_COLUMNS])
    if not rows:
        data.append([p('No proposals found for the selected filters.', cell)] + [''] * (n - 1))
        style.append(('SPAN', (0, 1), (-1, 1)))
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle(style))
    doc.build([Paragraph('Proposal Report', title),
               Paragraph(_xml_escape(f"{label}  |  {len(rows)} proposal{'s' if len(rows) != 1 else ''}  |  generated {_datetime.now(IST).strftime('%d-%b-%Y %H:%M')} IST"), sub),
               Spacer(1, 10), table], onFirstPage=on_page, onLaterPages=on_page)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------- routes
@app.route('/api/reports/proposals', methods=['GET'])
@login_required()
def reports_proposals():
    """?range=day|week|month|custom &date=YYYY-MM-DD &start= &end= &hr= &skill= &client= &format=json|xlsx|pdf"""
    fmt = (request.args.get('format') or 'json').strip().lower()
    if fmt not in ('json', 'xlsx', 'pdf'):
        return jsonify({'error': 'format must be json, xlsx or pdf'}), 400
    see_all = (session.get('role') or '').lower() in ('admin', 'manager')       # recruiters only ever see their own proposals
    try:
        start, end, label, rows = _report_query(request.args, session.get('user_id'), see_all)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    if fmt == 'json':
        resp = jsonify({'range': {'start': start.isoformat(), 'end': end.isoformat(), 'label': label},
                        'count': len(rows), 'columns': REPORT_COLUMNS, 'truncated': len(rows) >= REPORT_MAX_ROWS,
                        'rows': rows, 'groups': [{'date': d, 'label': _report_day_label(_date.fromisoformat(d)),
                                                  'count': sum(1 for x in rows if x['_date'] == d)}
                                                 for d in sorted({x['_date'] for x in rows})]})
    else:
        stem = f"Proposals_{start.isoformat()}" + ('' if start == end else f"_to_{end.isoformat()}")
        try:
            if fmt == 'xlsx':
                resp = send_file(_report_xlsx(rows, label), as_attachment=True, download_name=stem + '.xlsx',
                                 mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            else:
                resp = send_file(_report_pdf(rows, label), as_attachment=True, download_name=stem + '.pdf', mimetype='application/pdf')
        except Exception:
            app.logger.exception('proposal report export failed')
            return jsonify({'error': 'Could not build the report file'}), 500
    resp.headers['Cache-Control'] = 'no-store'                                    # contains phone numbers / emails
    return resp


@app.route('/api/reports/filter-options', methods=['GET'])
@login_required()
def reports_filter_options():
    see_all = (session.get('role') or '').lower() in ('admin', 'manager')
    conn = sqlite3.connect(DB_PATH)
    try:
        hrs = [r[0] for r in conn.execute("SELECT DISTINCT sent_by_name FROM proposal_dispatch_log WHERE sent_by_name <> '' ORDER BY 1")] if see_all else []
        clients = [r[0] for r in conn.execute(
            """SELECT name FROM (SELECT client_name AS name FROM requirements UNION SELECT proposed_client FROM candidates)
               WHERE name IS NOT NULL AND TRIM(name) <> '' ORDER BY 1""")]
    finally:
        conn.close()
    return jsonify({'hr': hrs, 'clients': clients, 'see_all': see_all})
