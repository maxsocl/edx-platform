
[:lms, :cms, :common].each do |system|
    report_dir = report_dir_path(system)
    directory report_dir

    desc "Run pep8 on all #{system} code"
    task "pep8_#{system}" => [report_dir, :install_python_prereqs] do
        sh("pep8 #{system} | tee #{report_dir}/pep8.report")
    end
    task :pep8 => "pep8_#{system}"

    desc "Run pylint on all #{system} code"
    task "pylint_#{system}" => [report_dir, :install_python_prereqs] do
        apps = Dir["#{system}/*.py", "#{system}/djangoapps/*", "#{system}/lib/*"].map do |app|
            File.basename(app)
        end.select do |app|
            app !=~ /.pyc$/
        end.map do |app|
            if app =~ /.py$/
                app.gsub('.py', '')
            else
                app
            end
        end

        pythonpath_prefix = "PYTHONPATH=#{system}:#{system}/djangoapps:#{system}/lib:common/djangoapps:common/lib"
        sh("#{pythonpath_prefix} pylint --rcfile=.pylintrc -f parseable #{apps.join(' ')} | tee #{report_dir}/pylint.report")
    end
    task :pylint => "pylint_#{system}"

end