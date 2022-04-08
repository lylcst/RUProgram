

function loadFile(url, callback) {
	PizZipUtils.getBinaryContent(url, callback); // 将文件加载成二进制文件
}

function generate(data, lang, collection_key) {
	// http://file.dearestli.com/doc/test.docx
      var doc_path = ""
	  if (lang)
	  	doc_path = 'static/ru_en.docx'
	  else doc_path = 'static/ru_ch.docx'
	  console.log(doc_path);
	  loadFile(doc_path, function(error, content) {
		  if (error) { throw error; }
		  const zip = PizZip(content); // 将内容转化PizZip对象

		  const doc = new docxtemplater().loadZip(zip); // 获得templater对象

		  // 对word中的变量进行赋值
		  var res = {}
		  for(var i=0;i<data.length;i++){
			// en_data = translate(data[i]);
			// console.log(en_data);
			// data[i]["content_en_"+i.toString()] = en_data
		  	res = Object.assign(res, data[i]);
		  }
		  doc.setData(res);

		  try {
			doc.render(); // 将赋值渲染到word数据中
		  } catch (error) {
			  const e = {
				  message: error.message,
				  name: error.name,
				  stack: error.stack,
				  properties: error.properties,
			  };
			  console.log(JSON.stringify({error: e}));
			  throw error;
		  }
		  // 生成输出数据，数据类型为FileSaver插件可以识别的blob类型,还可以生成string, base64, uint8array, arraybuffer类型
		  console.log(doc.getZip().generate)
		  const out = doc.getZip().generate({
			type: 'blob'
		  });
		  saveAs(out, collection_key+'.docx'); // 保存，并输出
	  });
  }

function translate(data) {
	var data_ = {"trans_data": data};
	console.log(data_);
	$.ajax({
		url: '/translate',
		type: 'GET',
		data: data_,
		success: function(res){
			console.log(res, "ajax");
			return res;
		},
		error: function(){
			console.log('有错误');
		},
		done: function (res) {
			console.log('结束');
			return res;
		}
	})
}

