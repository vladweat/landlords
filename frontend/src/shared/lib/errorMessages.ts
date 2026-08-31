const ERROR_MAP: Record<string, string> = {
  'Contract with this property already active': 'На этот объект уже есть активный контракт',
  'Payment amount exceeds charge remaining': 'Сумма платежа превышает остаток по начислению',
  'Cannot delete contract with payments': 'Нельзя удалить контракт, по которому есть платежи',
  'Invalid credentials': 'Неверный email или пароль',
  'Account already exists': 'Пользователь с таким email уже зарегистрирован',
  'Property has active contracts': 'Нельзя удалить объект с активным контрактом',
  'Tenant has active contracts': 'Нельзя удалить арендатора с активным контрактом',
};

export function getUserMessage(backendError: string): string {
  if (ERROR_MAP[backendError]) return ERROR_MAP[backendError];
  for (const [key, value] of Object.entries(ERROR_MAP)) {
    if (backendError.includes(key)) return value;
  }
  return 'Что-то пошло не так. Попробуйте ещё раз.';
}
