import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/main.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const TurtleApp());
    expect(find.text('터틀 트레이딩'), findsNothing); // AppBar는 하위 screen에서 렌더링
  });
}
