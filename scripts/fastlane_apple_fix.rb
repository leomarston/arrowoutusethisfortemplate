# Two upstream breakages stand between this factory and `fastlane produce`, and both are
# outside our code. Load this ahead of fastlane:
#
#   RUBYOPT="-r$PWD/scripts/fastlane_apple_fix" fastlane create_app
#
# 1. Ruby 4.0 removed CGI.parse from the default `cgi` library, but spaceship still calls it.
#    The full implementation is in the `cgi` GEM, which the default gem shadows unless it is
#    activated before `require`.  (gem install cgi)
#
# 2. Apple's service-key endpoint moved. `https://appstoreconnect.apple.com/olympus/v1/app/config`
#    now returns 404 for everyone — it is an UNAUTHENTICATED endpoint, so this is not a session
#    problem and re-authenticating cannot fix it (fastlane#30199). Without the key, spaceship
#    cannot begin an Apple ID login at all, which is the only way to create an app record: the
#    REST API answers POST /v1/apps with 403 "resource 'apps' does not allow 'CREATE'".
#    The key itself is a public constant — it is the widgetKey in the App Store Connect sign-in
#    URL — so we supply it instead of fetching it, and fall back to the real fetch if Apple
#    brings the endpoint back.
begin
  gem 'cgi'
  require 'cgi'
rescue Gem::LoadError, LoadError
end

ASC_WIDGET_KEY = "e0b80c3bf78523bfe80974d320935bfa30add02e1bff88ec2166c6bd5a706c42".freeze

# spaceship is not on the load path this early — RUBYOPT runs before fastlane sets up its own
# gem environment. So hook `require` and install the patch the moment spaceship's client lands.
module AppleFixLoader
  def require(path)
    loaded = super
    if loaded && !AppleFixLoader.patched && defined?(::Spaceship::Client) &&
       ::Spaceship::Client.method_defined?(:fetch_service_key)
      AppleFixLoader.install!
    end
    loaded
  end

  class << self
    attr_accessor :patched

    def install!
      self.patched = true
      ::Spaceship::Client.class_eval do
        alias_method :fetch_service_key_upstream, :fetch_service_key

        def fetch_service_key
          key = begin
            fetch_service_key_upstream
          rescue StandardError
            nil
          end
          return key if key && !key.to_s.empty?
          warn("[apple-fix] olympus service-key endpoint is down; using the public widget key")
          ASC_WIDGET_KEY
        end
      end
    end
  end
end

Object.prepend(AppleFixLoader)
