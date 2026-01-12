#include <iostream>
#include <string>
#include <chrono>
#include <sstream>

// Minimal NDJSON engine stub:
// - reads one JSON object per line from stdin
// - emits one JSON object per line to stdout
// This is NOT a full matching engine; it's a "bridge-compatible" simulator.

static std::string now_ms() {
    using namespace std::chrono;
    auto ms = duration_cast<milliseconds>(system_clock::now().time_since_epoch()).count();
    return std::to_string(ms);
}

static std::string escape_json(const std::string& s) {
    std::ostringstream out;
    for (char c : s) {
        switch (c) {
            case '\\': out << "\\\\"; break;
            case '"':  out << "\\\""; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default: out << c; break;
        }
    }
    return out.str();
}

// Extremely naive "field extractor" (for stub only).
// Assumes the input line contains: "key": <value> or "key":"value"
static std::string get_string_field(const std::string& json, const std::string& key) {
    std::string pat = "\"" + key + "\"";
    auto kpos = json.find(pat);
    if (kpos == std::string::npos) return "";
    auto colon = json.find(':', kpos + pat.size());
    if (colon == std::string::npos) return "";
    auto first_quote = json.find('"', colon);
    if (first_quote == std::string::npos) return "";
    auto second_quote = json.find('"', first_quote + 1);
    if (second_quote == std::string::npos) return "";
    return json.substr(first_quote + 1, second_quote - first_quote - 1);
}

static double get_number_field(const std::string& json, const std::string& key, double def = 0.0) {
    std::string pat = "\"" + key + "\"";
    auto kpos = json.find(pat);
    if (kpos == std::string::npos) return def;
    auto colon = json.find(':', kpos + pat.size());
    if (colon == std::string::npos) return def;

    // Find start of number
    size_t start = colon + 1;
    while (start < json.size() && (json[start] == ' ')) start++;
    size_t end = start;
    while (end < json.size() && (isdigit((unsigned char)json[end]) || json[end] == '.' || json[end] == '-')) end++;

    try {
        return std::stod(json.substr(start, end - start));
    } catch (...) {
        return def;
    }
}

int main() {
    // Announce ready (helps debugging)
    std::cout << "{\"type\":\"engine_status\",\"status\":\"ready\",\"ts_ms\":" << now_ms() << "}\n";
    std::cout.flush();

    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;

        // Parse minimal fields expected from Python Order model
        std::string order_id = get_string_field(line, "order_id");
        std::string symbol   = get_string_field(line, "symbol");
        std::string side     = get_string_field(line, "side");
        double qty           = get_number_field(line, "qty", 0.0);
        double px            = get_number_field(line, "px", 0.0);

        // Emit an ACK
        std::cout
            << "{\"type\":\"ack\","
            << "\"order_id\":\"" << escape_json(order_id) << "\","
            << "\"symbol\":\"" << escape_json(symbol) << "\","
            << "\"ts_ms\":" << now_ms()
            << "}\n";

        // Emit a simulated FILL (instant)
        std::cout
            << "{\"type\":\"fill\","
            << "\"order_id\":\"" << escape_json(order_id) << "\","
            << "\"symbol\":\"" << escape_json(symbol) << "\","
            << "\"side\":\"" << escape_json(side) << "\","
            << "\"qty\":" << qty << ","
            << "\"px\":" << px << ","
            << "\"ts_ms\":" << now_ms()
            << "}\n";

        std::cout.flush();
    }

    return 0;
}
