import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'api_service.dart';

/// 백그라운드 메시지 핸들러 — 반드시 최상위 함수여야 함
@pragma('vm:entry-point')
Future<void> _onBackgroundMessage(RemoteMessage message) async {
  // 앱이 종료/백그라운드 상태일 때 FCM이 자동 처리
  // 별도 작업 불필요 (data-only 메시지 처리 시 여기서 처리)
}

class NotificationService {
  static final _messaging = FirebaseMessaging.instance;
  static final _localNotifications = FlutterLocalNotificationsPlugin();

  static const _channelId = 'turtle_signals';
  static const _channelName = '터틀 신호';
  static const _channelDesc = '터틀 트레이딩 매매 신호 알림';

  static Future<void> initialize() async {
    // 백그라운드 핸들러 등록
    FirebaseMessaging.onBackgroundMessage(_onBackgroundMessage);

    // 알림 권한 요청
    final settings = await _messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    if (settings.authorizationStatus == AuthorizationStatus.denied) {
      return; // 권한 거부 시 중단
    }

    // Android 알림 채널 생성 (Android 8.0+)
    const channel = AndroidNotificationChannel(
      _channelId,
      _channelName,
      description: _channelDesc,
      importance: Importance.high,
    );
    await _localNotifications
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channel);

    // flutter_local_notifications 초기화 (포그라운드 알림용)
    const androidSettings =
        AndroidInitializationSettings('@mipmap/ic_launcher');
    await _localNotifications.initialize(
      //const InitializationSettings(android: androidSettings),
      settings: const InitializationSettings(android: androidSettings),
    );

    // 포그라운드 메시지 → 로컬 알림으로 표시
    FirebaseMessaging.onMessage.listen(_showLocalNotification);

    // FCM 토큰 발급 및 백엔드 등록
    await _registerToken();

    // 토큰 갱신 시 자동 재등록
    _messaging.onTokenRefresh.listen((token) async {
      await ApiService.registerFcmToken(token);
    });
  }

  static Future<void> _registerToken() async {
    try {
      final token = await _messaging.getToken();
      if (token != null) {
        await ApiService.registerFcmToken(token);
      }
    } catch (e) {
      // 서버 미연결 상태에서도 앱 정상 동작해야 함
    }
  }

  static Future<void> _showLocalNotification(RemoteMessage message) async {
    final notification = message.notification;
    if (notification == null) return;

    await _localNotifications.show(
     id: notification.hashCode,
  title: notification.title,
  body: notification.body,
  notificationDetails: const NotificationDetails(
    android: AndroidNotificationDetails(
      _channelId,
      _channelName,
      channelDescription: _channelDesc,
      importance: Importance.high,
      priority: Priority.high,
       icon: '@mipmap/ic_launcher',
        ),
      ),
    );
  }
}
