const ERROR_MAP: Record<string, string> = {
  'Contract with this property already active': 'На этот объект уже есть активный контракт',
  'Payment amount exceeds charge remaining': 'Сумма платежа превышает остаток по начислению',
  'Charge does not belong to this contract': 'Начисление не принадлежит выбранному договору',
  'Charge is already fully paid': 'Начисление уже полностью оплачено',
  'Cannot delete contract with payments': 'Нельзя удалить контракт, по которому есть платежи',
  'Invalid credentials': 'Неверный email или пароль',
  'Account already exists': 'Пользователь с таким email уже зарегистрирован',
  'Property has active contracts': 'Нельзя удалить объект с активным контрактом',
  'Tenant has active contracts': 'Нельзя удалить арендатора с активным контрактом',
  'timeout of': 'Сервер долго не отвечает. Попробуйте ещё раз.',
  'Network Error': 'Нет связи с сервером. Проверьте сеть.',
};

const TECHNICAL = [
  /^request failed with status code \d+$/i,
  /^timeout of \d+ms exceeded$/i,
  /^network error$/i,
  /^failed to fetch$/i,
];

export function getUserMessage(backendError: string): string {
  if (ERROR_MAP[backendError]) return ERROR_MAP[backendError];
  for (const [key, value] of Object.entries(ERROR_MAP)) {
    if (backendError.includes(key)) return value;
  }
  // Не прячем понятные сообщения с бэка (в т.ч. русские AppException)
  if (backendError && !TECHNICAL.some((re) => re.test(backendError.trim()))) {
    return backendError;
  }
  return 'Что-то пошло не так. Попробуйте ещё раз.';
}
