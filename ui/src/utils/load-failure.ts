const FALLBACK_PATH = './noscript/books.html'

export function renderLoadFailure(container: HTMLElement): void {
  container.innerHTML = `
    <div style="max-width: 600px; margin: 50px auto; padding: 20px; text-align: center;">
      <div style="background: #f8f9fa; padding: 30px; border-radius: 8px; border-left: 4px solid #3498db;">
        <h1 style="color: #2c3e50; margin-bottom: 20px;">The default ZIM interface could not start</h1>
        <p style="margin: 15px 0; color: #666;">Even if unlikely to succeed, you might want to try reloading the page or the ZIM.</p>
        <p style="margin: 15px 0; color: #666;">You might be interested to know there is another more limited interface which might work for your setup:</p>
        <a href="${FALLBACK_PATH}" style="display: inline-block; margin-top: 20px; padding: 12px 24px; background: #3498db; color: #fff; text-decoration: none; border-radius: 5px; font-weight: 500;">Go to No-JavaScript interface</a>
      </div>
    </div>
  `
}
