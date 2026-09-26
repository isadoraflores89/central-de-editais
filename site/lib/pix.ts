// PIX estático "copia e cola" (BR Code), conforme o Manual de Padrões para
// Iniciação do PIX do Banco Central. Sem valor fixo: a pessoa escolhe quanto doar.

function campo(id: string, valor: string): string {
  return id + String(valor.length).padStart(2, "0") + valor;
}

export function crc16(payload: string): string {
  let crc = 0xffff;
  for (const ch of payload) {
    crc ^= ch.charCodeAt(0) << 8;
    for (let i = 0; i < 8; i++) {
      crc = crc & 0x8000 ? ((crc << 1) ^ 0x1021) & 0xffff : (crc << 1) & 0xffff;
    }
  }
  return crc.toString(16).toUpperCase().padStart(4, "0");
}

function limpar(texto: string, max: number): string {
  return texto.normalize("NFD").replace(/\p{Mn}/gu, "").replace(/[^A-Za-z0-9 .-]/g, "").slice(0, max);
}

export function brCode(chave: string, nome: string, cidade: string, txid = "***"): string {
  const conta = campo("00", "br.gov.bcb.pix") + campo("01", chave.trim());
  const semCrc =
    campo("00", "01") +
    campo("26", conta) +
    campo("52", "0000") +
    campo("53", "986") +
    campo("58", "BR") +
    campo("59", limpar(nome, 25)) +
    campo("60", limpar(cidade, 15)) +
    campo("62", campo("05", txid)) +
    "6304";
  return semCrc + crc16(semCrc);
}
