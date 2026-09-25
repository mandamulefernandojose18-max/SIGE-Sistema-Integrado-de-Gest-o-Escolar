import QRCode from 'qrcode';

export async function generateQrCodeDataUrl(data: string): Promise<string> {
  try {
    return await QRCode.toDataURL(data, {
      errorCorrectionLevel: 'M',
      margin: 2,
      width: 256,
      color: {
        dark: '#1e293b',
        light: '#ffffff'
      }
    });
  } catch (error) {
    console.error('Erro ao gerar QRCode:', error);
    throw new Error('Falha na geração do QR Code de autenticidade');
  }
}
