export class BarcodeScanner {
  static async scanFromCamera(): Promise<string | null> {
    if (!navigator.mediaDevices?.getUserMedia) return null

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
      })

      const video = document.createElement('video')
      video.srcObject = stream
      video.setAttribute('playsinline', 'true')
      await video.play()

      const canvas = document.createElement('canvas')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight

      const ctx = canvas.getContext('2d')
      if (!ctx) {
        stream.getTracks().forEach(t => t.stop())
        return null
      }

      return new Promise((resolve) => {
        const MAX_ATTEMPTS = 30
        let attempts = 0

        const scan = () => {
          ctx.drawImage(video, 0, 0)
          const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)

          const code = this.decodeBarcode(imageData)
          if (code) {
            stream.getTracks().forEach(t => t.stop())
            resolve(code)
            return
          }

          attempts++
          if (attempts >= MAX_ATTEMPTS) {
            stream.getTracks().forEach(t => t.stop())
            resolve(null)
            return
          }

          requestAnimationFrame(scan)
        }

        scan()
      })
    } catch {
      return null
    }
  }

  private static decodeBarcode(_imageData: ImageData): string | null {
    return null
  }

  static async capturePhoto(): Promise<Blob | null> {
    if (!navigator.mediaDevices?.getUserMedia) return null

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
      })

      const video = document.createElement('video')
      video.srcObject = stream
      video.setAttribute('playsinline', 'true')
      await video.play()

      return new Promise((resolve) => {
        setTimeout(() => {
          const canvas = document.createElement('canvas')
          canvas.width = video.videoWidth
          canvas.height = video.videoHeight
          const ctx = canvas.getContext('2d')
          if (!ctx) {
            stream.getTracks().forEach(t => t.stop())
            resolve(null)
            return
          }
          ctx.drawImage(video, 0, 0)
          stream.getTracks().forEach(t => t.stop())
          canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.85)
        }, 500)
      })
    } catch {
      return null
    }
  }
}

export class VoiceInput {
  private recognition: SpeechRecognition | null = null

  async start(lang: string = 'zh-CN'): Promise<string> {
    return new Promise((resolve, reject) => {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
      if (!SpeechRecognition) {
        reject(new Error('Speech recognition not supported'))
        return
      }

      this.recognition = new SpeechRecognition()
      this.recognition.lang = lang
      this.recognition.continuous = false
      this.recognition.interimResults = false

      this.recognition.onresult = (event: SpeechRecognitionEvent) => {
        const transcript = event.results[0][0].transcript
        resolve(transcript)
      }

      this.recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        reject(new Error(event.error))
      }

      this.recognition.onend = () => {
        this.recognition = null
      }

      this.recognition.start()
    })
  }

  stop(): void {
    this.recognition?.stop()
    this.recognition = null
  }
}

declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition
    webkitSpeechRecognition: typeof SpeechRecognition
  }
}