const {watch} = require('gulp');
const gulp = require('gulp')
const browserSync = require('browser-sync').create();
const reload = browserSync.reload;

gulp.task('browser-sync', function () {
    browserSync.init({
        server: {
            baseDir: "./",
            port: 3001
        }
    });
});

gulp.task('default', gulp.parallel('browser-sync', function () {
    watch(['./**/*'], function (done) {
        reload()
        done()
    });
}))

