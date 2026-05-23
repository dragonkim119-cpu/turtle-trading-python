import 'package:flutter/material.dart';
import '../services/watchlist_service.dart';
import '../services/api_service.dart';

class WatchlistScreen extends StatefulWidget {
  const WatchlistScreen({super.key});
  @override
  State<WatchlistScreen> createState() => _WatchlistScreenState();
}

class _WatchlistScreenState extends State<WatchlistScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabs;
  Map<String, List<Map<String, String>>> _watchlist = {};
  Map<String, Map<String, dynamic>> _status = {}; // symbol → status info
  bool _loading = false;
  bool _scanning = false;

  static const _categories = [
    ('domestic', '국내주식'),
    ('overseas', '해외주식'),
    ('crypto', '가상자산'),
  ];

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
    _loadWatchlist();
  }

  Future<void> _loadWatchlist() async {
    setState(() => _loading = true);
    final data = await WatchlistService.load();
    setState(() { _watchlist = Map.from(data); _loading = false; });
  }

  Future<void> _scan() async {
    setState(() => _scanning = true);
    try {
      // 전체 종목 수집
      final allItems = <Map<String, String>>[];
      _watchlist.forEach((type, items) {
        for (final item in items) {
          allItems.add({
            'symbol': item['symbol']!,
            'name': item['name'] ?? item['symbol']!,
            'asset_type': type,
            'exchange': type == 'overseas' ? 'NAS' : '',
          });
        }
      });

      final results = await ApiService.getWatchlistStatus(allItems, 100000000);
      final newStatus = <String, Map<String, dynamic>>{};
      for (final r in results) {
        newStatus[r['symbol'] as String] = r;
      }
      setState(() => _status = newStatus);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('스캔 오류: $e')),
        );
      }
    } finally {
      setState(() => _scanning = false);
    }
  }

  Future<void> _addDialog(String type) async {
    final symbolCtrl = TextEditingController();
    final nameCtrl = TextEditingController();
    final hints = {
      'domestic': ('005930', '삼성전자'),
      'overseas': ('GOOGL', 'Alphabet'),
      'crypto': ('KRW-ADA', 'Cardano'),
    };
    final hint = hints[type]!;

    await showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('종목 추가'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: symbolCtrl,
              decoration: InputDecoration(
                labelText: '종목코드',
                hintText: hint.$1,
                border: const OutlineInputBorder(),
              ),
              textCapitalization: TextCapitalization.characters,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: nameCtrl,
              decoration: InputDecoration(
                labelText: '종목명',
                hintText: hint.$2,
                border: const OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('취소')),
          ElevatedButton(
            onPressed: () async {
              final sym = symbolCtrl.text.trim().toUpperCase();
              final name = nameCtrl.text.trim();
              if (sym.isEmpty) return;
              await WatchlistService.add(type, sym, name.isEmpty ? sym : name);
              if (ctx.mounted) Navigator.pop(ctx);
              await _loadWatchlist();
            },
            child: const Text('추가'),
          ),
        ],
      ),
    );
  }

  Future<void> _delete(String type, String symbol) async {
    await WatchlistService.remove(type, symbol);
    _status.remove(symbol);
    await _loadWatchlist();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('종목 관리'),
        actions: [
          if (_scanning)
            const Padding(
              padding: EdgeInsets.all(14),
              child: SizedBox(width: 20, height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)),
            )
          else
            IconButton(
              icon: const Icon(Icons.search),
              tooltip: '신호 스캔',
              onPressed: _scan,
            ),
        ],
        bottom: TabBar(
          controller: _tabs,
          tabs: _categories.map((c) => Tab(text: c.$2)).toList(),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : TabBarView(
              controller: _tabs,
              children: _categories.map((c) => _buildList(c.$1)).toList(),
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _addDialog(_categories[_tabs.index].$1),
        child: const Icon(Icons.add),
        tooltip: '종목 추가',
      ),
    );
  }

  Widget _buildList(String type) {
    final items = _watchlist[type] ?? [];
    if (items.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.playlist_add, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text('종목 없음', style: TextStyle(color: Colors.grey)),
            Text('+ 버튼으로 추가', style: TextStyle(color: Colors.grey, fontSize: 12)),
          ],
        ),
      );
    }
    return ListView.builder(
      itemCount: items.length,
      itemBuilder: (ctx, i) {
        final item = items[i];
        final sym = item['symbol']!;
        final info = _status[sym];
        final statusStr = info?['status'] as String? ?? '미스캔';
        return _SymbolTile(
          symbol: sym,
          name: item['name'] ?? sym,
          status: statusStr,
          onDelete: () => _delete(type, sym),
        );
      },
    );
  }
}


class _SymbolTile extends StatelessWidget {
  final String symbol;
  final String name;
  final String status;
  final VoidCallback onDelete;

  const _SymbolTile({
    required this.symbol,
    required this.name,
    required this.status,
    required this.onDelete,
  });

  Color get _statusColor {
    switch (status) {
      case '매수': return Colors.green;
      case '매도': return Colors.red;
      case '청산': return Colors.orange;
      case '오류': return Colors.grey;
      default: return Colors.blueGrey;
    }
  }

  IconData get _statusIcon {
    switch (status) {
      case '매수': return Icons.arrow_upward;
      case '매도': return Icons.arrow_downward;
      case '청산': return Icons.exit_to_app;
      default: return Icons.horizontal_rule;
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Container(
        width: 42,
        height: 42,
        decoration: BoxDecoration(
          color: _statusColor.withOpacity(0.15),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: _statusColor, width: 1.5),
        ),
        child: Icon(_statusIcon, color: _statusColor, size: 20),
      ),
      title: Text(name, style: const TextStyle(fontWeight: FontWeight.w600)),
      subtitle: Text(symbol, style: TextStyle(color: Colors.grey[500], fontSize: 12)),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: _statusColor,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(status,
                style: const TextStyle(color: Colors.white,
                    fontSize: 12, fontWeight: FontWeight.bold)),
          ),
          const SizedBox(width: 4),
          IconButton(
            icon: const Icon(Icons.delete_outline, color: Colors.red, size: 20),
            onPressed: onDelete,
          ),
        ],
      ),
    );
  }
}
