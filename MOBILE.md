# Mobile App Integration Guide

CourseGenie is currently a responsive Flask web app. To distribute it as a native mobile app, you can wrap it in a WebView. Below are two recommended approaches.

## Option 1: Capacitor (Ionic)

**Capacitor** is a cross-platform runtime that lets you wrap your web app into iOS and Android apps.

### Setup

1. Install Node.js and npm (if you don't have them).

2. Install the Capacitor CLI globally:

   ```bash
   npm install -g @capacitor/cli @capacitor/core
   ```

3. In a new directory (or next to your Flask project), create a Capacitor project:

   ```bash
   npm init @capacitor/app
   cd your-capacitor-app
   ```

4. Build your Flask app's static assets or run it on a local server. Point the Capacitor `webDir` to your Flask `static` and `templates` folder, or simply configure it to load from `http://localhost:5000` in development.

5. Add iOS and Android platforms:

   ```bash
   npx cap add ios
   npx cap add android
   ```

6. Configure `capacitor.config.json` to point to your Flask app's URL (e.g., `http://localhost:5000` or a deployed server).

7. Open and run in Xcode or Android Studio:

   ```bash
   npx cap open ios
   npx cap open android
   ```

### Notes

- In production, deploy the Flask backend to a server and set the URL in `capacitor.config.json` to your production domain.
- Use the `/api/chat` endpoint (already added to `app.py`) for native mobile interactions.

---

## Option 2: Native WebView (Android / iOS)

If you prefer a minimal custom approach:

### Android (Kotlin/Java)

1. Create a new Android project in Android Studio.
2. Add a WebView to your main activity layout:

   ```xml
   <WebView
       android:id="@+id/webview"
       android:layout_width="match_parent"
       android:layout_height="match_parent" />
   ```

3. In your `MainActivity`, load the Flask app URL:

   ```kotlin
   val webView: WebView = findViewById(R.id.webview)
   webView.settings.javaScriptEnabled = true
   webView.loadUrl("https://your-deployed-flask-app.com")
   ```

4. Build and run the APK.

### iOS (Swift)

1. Create a new Xcode project.
2. Add a `WKWebView` to your ViewController:

   ```swift
   import WebKit

   class ViewController: UIViewController {
       var webView: WKWebView!

       override func viewDidLoad() {
           super.viewDidLoad()
           webView = WKWebView(frame: view.bounds)
           view.addSubview(webView)
           let url = URL(string: "https://your-deployed-flask-app.com")!
           webView.load(URLRequest(url: url))
       }
   }
   ```

3. Build and run the app on a simulator or device.

---

## Next Steps

- Deploy your Flask backend to a cloud provider (Heroku, Render, AWS, etc.) so the mobile app can access it.
- Test the `/api/chat` endpoint from the mobile app using `fetch` or native HTTP libraries if you want to bypass the web UI and build a fully native chat interface.
- Configure app icons, splash screens, and permissions as needed.

For a quick start, **Capacitor** is the easiest and most flexible option for cross-platform development.
