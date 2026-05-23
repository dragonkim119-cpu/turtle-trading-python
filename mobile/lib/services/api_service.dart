import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import '../models/signal.dart';

class ApiService {
  static const _defaultUrl = 'http://10.0.2.2:8000';
  static String? _cachedUrl;

  static Future<File> _configFile() async {
    final dir = await getApplicationDocumentsDirectory();
    return File('${dir.path}/turtle_config.json');
  }

  static Future<String> getBaseUrl() async {
    if (_cachedUrl != null) return _cachedUrl!;
    try {
      final file = await _configFile();
      if (await file.exists()) {
        final data = jsonDecode(await file.readAsString());
        _cachedUrl = data['base_url'] ?? _defaultUrl;
        return _cachedUrl!;
      }
    } catch (_) {}
    return _defaultUrl;
  }

  static Future<void> setBaseUrl(String url) async {
    _cachedUrl = url;
    final file = await _configFile();
    await file.writeAsString(jsonEncode({'base_url': url}));
  }

  static Future<List<TurtleSignal>> getSignals({
    String? assetType,
    String? signalType,
  }) async {
    final base = await getBaseUrl();
    final params = <String, String>{};
    if (assetType != null) params['asset_type'] = assetType;
    if (signalType != null) params['signal_type'] = signalType;

    final uri = Uri.parse('$base/api/v1/signals').replace(queryParameters: params);
    final resp = await http.get(uri).timeout(const Duration(seconds: 10));

    if (resp.statusCode != 200) throw Exception('신호 조회 실패: ${resp.statusCode}');
    final data = jsonDecode(utf8.decode(resp.bodyBytes));
    return (data['signals'] as List)
        .map((e) => TurtleSignal.fromJson(e))
        .toList();
  }

  static Future<int> triggerScan() async {
    final base = await getBaseUrl();
    final resp = await http
        .post(Uri.parse('$base/api/v1/signals/scan'))
        .timeout(const Duration(seconds: 120));

    if (resp.statusCode != 200) throw Exception('스캔 실패: ${resp.statusCode}');
    final data = jsonDecode(utf8.decode(resp.bodyBytes));
    return data['count'] as int;
  }

  static Future<List<Map<String, dynamic>>> getWatchlistStatus(
      List<Map<String, String>> items, double balance) async {
    final base = await getBaseUrl();
    final body = jsonEncode({
      'account_balance': balance,
      'items': items.map((e) => {
        'symbol': e['symbol'],
        'name': e['name'] ?? e['symbol'],
        'asset_type': e['asset_type'],
        'exchange': e['exchange'] ?? 'NAS',
      }).toList(),
    });
    final resp = await http
        .post(Uri.parse('$base/api/v1/signals/watchlist-status'),
            headers: {'Content-Type': 'application/json'}, body: body)
        .timeout(const Duration(seconds: 120));
    if (resp.statusCode != 200) throw Exception('상태 조회 실패');
    final data = jsonDecode(utf8.decode(resp.bodyBytes));
    return List<Map<String, dynamic>>.from(data['items']);
  }

  static Future<bool> checkHealth() async {
    try {
      final base = await getBaseUrl();
      final resp = await http
          .get(Uri.parse('$base/health'))
          .timeout(const Duration(seconds: 5));
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}
