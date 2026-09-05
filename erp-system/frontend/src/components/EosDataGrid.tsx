import { useEffect, useMemo, useState } from 'react';
import { FiChevronDown, FiChevronLeft, FiChevronRight, FiSearch, FiSettings } from 'react-icons/fi';
import { dynamicAPI, type DynamicColumn, type DynamicListSchema } from '../services/dynamic';

type Props = { entityCode: string; language: 'ar' | 'en' };
type Filter = { field: string; operator: 'eq' | 'like'; value: string };

const demoRows: Record<string, unknown>[] = [
  { name: 'Acme Industries', email: 'finance@acme.example', amount: '€24,500', status: 'Active' },
  { name: 'Northstar Group', email: 'ops@northstar.example', amount: '€18,200', status: 'Active' },
  { name: 'Cedar Trading', email: 'hello@cedar.example', amount: '€9,840', status: 'Pending' },
  { name: 'Atlas Construction', email: 'accounts@atlas.example', amount: '€7,620', status: 'Active' },
];

export default function EosDataGrid({ entityCode, language }: Props) {
  const [schema, setSchema] = useState<DynamicListSchema | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [limit] = useState(50);
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState('');
  const [filter, setFilter] = useState<Filter>({ field: '', operator: 'like', value: '' });
  const [loading, setLoading] = useState(true);
  const [remoteError, setRemoteError] = useState(false);

  useEffect(() => {
    let alive = true;
    dynamicAPI.listSchema(entityCode).then((response) => alive && setSchema(response.data.data)).catch(() => alive && setSchema(null));
    return () => { alive = false; };
  }, [entityCode]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setRemoteError(false);
    const activeFilter = filter.field && filter.value ? `${filter.field}:${filter.operator}:${filter.value.replaceAll(',', ' ')}` : undefined;
    const searchFilter = search ? `name:like:${search.replaceAll(',', ' ')}` : undefined;
    const filters = [activeFilter, searchFilter].filter(Boolean).join(',') || undefined;
    dynamicAPI.records(entityCode, { filters, sort: sort || undefined, limit, offset })
      .then((response) => { if (alive) { setRows(response.data.data || []); setTotal(response.data.pagination?.total ?? response.data.count ?? 0); } })
      .catch(() => { if (alive) { setRows(demoRows); setTotal(demoRows.length); setRemoteError(true); } })
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [entityCode, filter.field, filter.operator, filter.value, limit, offset, search, sort]);

  const columns = useMemo<DynamicColumn[]>(() => schema?.columns?.length ? schema.columns : [
    { field: 'name', label: 'Customer', label_ar: 'العميل', sortable: true },
    { field: 'email', label: 'Email', label_ar: 'البريد الإلكتروني' },
    { field: 'amount', label: 'Amount', label_ar: 'القيمة', sortable: true },
    { field: 'status', label: 'Status', label_ar: 'الحالة' },
  ], [schema]);

  const toggleSort = (column: DynamicColumn) => {
    if (!column.sortable) return;
    setOffset(0);
    setSort(sort === column.field ? `-${column.field}` : column.field);
  };

  return <div className="eos-card eos-table-card">
    <div className="eos-table-toolbar">
      <div className="eos-search eos-table-search"><FiSearch /><input value={search} onChange={(event) => { setOffset(0); setSearch(event.target.value); }} placeholder={language === 'ar' ? 'بحث في السجلات' : 'Search records'} /></div>
      <div className="eos-grid-filter">
        <select aria-label={language === 'ar' ? 'الحقل' : 'Field'} value={filter.field} onChange={(e) => { setOffset(0); setFilter({ ...filter, field: e.target.value }); }}>
          <option value="">{language === 'ar' ? 'تصفية' : 'Filter'}</option>
          {columns.map((column) => <option key={column.field} value={column.field}>{language === 'ar' ? column.label_ar || column.label : column.label || column.field}</option>)}
        </select>
        <input value={filter.value} onChange={(e) => { setOffset(0); setFilter({ ...filter, value: e.target.value }); }} placeholder={language === 'ar' ? 'القيمة' : 'Value'} />
      </div>
      <button className="eos-ghost-button" type="button"><FiSettings /> {language === 'ar' ? 'الأعمدة' : 'Columns'}</button>
    </div>
    {remoteError && <div className="eos-grid-demo-note">{language === 'ar' ? 'وضع العرض التجريبي — سجّل الدخول لتحميل بيانات شركتك.' : 'Demo mode — sign in to load your tenant data.'}</div>}
    <div className="eos-table-wrap"><table><thead><tr><th className="eos-select-cell"><input type="checkbox" aria-label={language === 'ar' ? 'تحديد الكل' : 'Select all'} /></th>{columns.map((column) => <th key={column.field}><button className="eos-sort-button" type="button" onClick={() => toggleSort(column)}>{language === 'ar' ? column.label_ar || column.label : column.label || column.field}{column.sortable && <FiChevronDown />}</button></th>)}</tr></thead>
      <tbody>{loading ? <tr><td colSpan={columns.length + 1} className="eos-grid-state">{language === 'ar' ? 'جاري التحميل…' : 'Loading…'}</td></tr> : rows.length === 0 ? <tr><td colSpan={columns.length + 1} className="eos-grid-state">{language === 'ar' ? 'لا توجد سجلات' : 'No records found'}</td></tr> : rows.map((row, index) => <tr key={String(row.id ?? index)}><td className="eos-select-cell"><input type="checkbox" aria-label={`Select row ${index + 1}`} /></td>{columns.map((column) => <td key={column.field}>{column.maskable ? '••••••' : String(row[column.field] ?? '—')}</td>)}</tr>)}</tbody>
    </table></div>
    <div className="eos-table-footer"><span>{language === 'ar' ? `عرض ${total ? offset + 1 : 0}–${Math.min(offset + limit, total)} من ${total}` : `Showing ${total ? offset + 1 : 0}–${Math.min(offset + limit, total)} of ${total}`}</span><div className="eos-pagination"><button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}><FiChevronLeft /></button><button type="button" disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}><FiChevronRight /></button></div></div>
  </div>;
}
