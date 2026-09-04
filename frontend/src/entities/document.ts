export type DocumentCategory =
  | 'contract_pdf'
  | 'passport'
  | 'act'
  | 'photo'
  | 'other';

export type DocumentSource = 'generated' | 'uploaded';

export type UploadDocumentCategory = Exclude<DocumentCategory, 'contract_pdf'>;

export interface DocumentItem {
  id: string;
  contract_id: string | null;
  property_id: string | null;
  filename: string;
  title: string;
  category: DocumentCategory | string;
  mime_type: string;
  size_bytes: number | null;
  source: DocumentSource | string;
  created_at: string | null;
  url: string;
}

export const DOCUMENT_CATEGORY_LABELS: Record<string, string> = {
  contract_pdf: 'Договор (PDF)',
  passport: 'Паспорт',
  act: 'Акт',
  photo: 'Фото',
  other: 'Прочее',
};

export const UPLOAD_CATEGORY_OPTIONS: { value: UploadDocumentCategory; label: string }[] = [
  { value: 'passport', label: 'Паспорт' },
  { value: 'act', label: 'Акт' },
  { value: 'photo', label: 'Фото' },
  { value: 'other', label: 'Прочее' },
];
