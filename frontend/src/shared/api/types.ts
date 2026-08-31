export interface ApiResponse<T> {
  status: 'success' | 'error';
  data: T;
}

export interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface ApiError {
  status: 'error';
  message: string;
}

export interface AuthResponse {
  status: 'success';
  token: string;
  user: {
    id: string;
    email: string;
    full_name: string;
  };
}
