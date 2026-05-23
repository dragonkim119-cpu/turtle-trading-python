import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';

class WatchlistService {
  static Map<String, List<Map<String, String>>>? _cache;

  static final _defaults = {
    'domestic': [
      {'symbol': '005930', 'name': '삼성전자'},
      {'symbol': '000660', 'name': 'SK하이닉스'},
      {'symbol': '035420', 'name': 'NAVER'},
      {'symbol': '051910', 'name': 'LG화학'},
      {'symbol': '035720', 'name': '카카오'},
    ],
    'overseas': [
      {'symbol': 'AAPL', 'name': 'Apple'},
      {'symbol': 'MSFT', 'name': 'Microsoft'},
      {'symbol': 'NVDA', 'name': 'NVIDIA'},
      {'symbol': 'TSLA', 'name': 'Tesla'},
      {'symbol': 'AMZN', 'name': 'Amazon'},
    ],
    'crypto': [
      {'symbol': 'KRW-BTC', 'name': 'Bitcoin'},
      {'symbol': 'KRW-ETH', 'name': 'Ethereum'},
      {'symbol': 'KRW-XRP', 'name': 'XRP'},
      {'symbol': 'KRW-SOL', 'name': 'Solana'},
    ],
  };

  static Future<File> _file() async {
    final dir = await getApplicationDocumentsDirectory();
    return File('${dir.path}/watchlist.json');
  }

  static Future<Map<String, List<Map<String, String>>>> load() async {
    if (_cache != null) return _cache!;
    try {
      final f = await _file();
      if (await f.exists()) {
        final raw = jsonDecode(await f.readAsString()) as Map<String, dynamic>;
        _cache = raw.map((k, v) => MapEntry(
          k,
          (v as List).map((e) => Map<String, String>.from(e)).toList(),
        ));
        return _cache!;
      }
    } catch (_) {}
    _cache = Map.from(_defaults.map((k, v) => MapEntry(k, List<Map<String, String>>.from(v))));
    return _cache!;
  }

  static Future<void> _save() async {
    final f = await _file();
    await f.writeAsString(jsonEncode(_cache));
  }

  static Future<List<Map<String, String>>> getCategory(String type) async {
    final data = await load();
    return data[type] ?? [];
  }

  static Future<void> add(String type, String symbol, String name) async {
    await load();
    final list = _cache![type] ??= [];
    if (list.any((e) => e['symbol'] == symbol)) return;
    list.add({'symbol': symbol, 'name': name});
    await _save();
  }

  static Future<void> remove(String type, String symbol) async {
    await load();
    _cache![type]?.removeWhere((e) => e['symbol'] == symbol);
    await _save();
  }
}
