import { Response } from 'express';

export function sendSuccess<T>(res: Response, data: T, message?: string, statusCode = 200) {
  return res.status(statusCode).json({
    success: true,
    message,
    data
  });
}

export function sendError(
  res: Response,
  message: string,
  statusCode = 400,
  errorCode = 'BAD_REQUEST',
  details?: any
) {
  return res.status(statusCode).json({
    success: false,
    error: errorCode,
    message,
    details
  });
}
