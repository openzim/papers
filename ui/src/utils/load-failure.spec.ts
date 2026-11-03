import { describe, expect, it } from 'vitest'
import { renderLoadFailure } from './load-failure'

describe('renderLoadFailure', () => {
  it('frames reloading as an unlikely fix', () => {
    const container = document.createElement('div')

    renderLoadFailure(container)

    expect(container.textContent).toContain(
      'Even if unlikely to succeed, you might want to try reloading the page or the ZIM.'
    )
    expect(container.textContent).not.toContain('Please refresh')
  })

  it('links to the more limited No-JavaScript interface', () => {
    const container = document.createElement('div')

    renderLoadFailure(container)

    expect(container.textContent).toContain('another more limited interface')
    const link = container.querySelector('a')
    expect(link?.getAttribute('href')).toBe('./noscript/books.html')
    expect(link?.textContent).toBe('Go to No-JavaScript interface')
  })
})
